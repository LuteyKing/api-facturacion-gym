"""
Endpoint POST /api/v1/facturar — Orquestación del flujo completo.

Recibe un JSON simplificado con datos del cliente y productos,
y ejecuta automáticamente:

  1. Calcular impuestos y totales a partir de los productos.
  2. Armar el FacturaRequest interno (estructura SRI).
  3. Generar la clave de acceso (49 dígitos, Módulo 11).
  4. Construir el XML de la factura (lxml).
  5. Firmar el XML con XAdES-BES (certificado .p12).
  5.5 Guardar la factura en la base de datos SQLite.
  6. Enviar al WS RecepcionComprobantesOffline (zeep).
  7. Consultar el WS AutorizacionComprobantesOffline (zeep).
  8. Actualizar el estado del SRI en la BD.
  9. Retornar la respuesta unificada.
"""

import base64
import logging
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..models.enums import (
    CodigoImpuesto,
    CodigoPorcentajeIVA,
    FormaPago,
    TARIFA_IVA,
    TipoDocumento,
)
from ..models.schemas import (
    AutorizacionResponse,
    ClienteFactura,
    DetalleFactura,
    FacturarRequest,
    FacturaRequest,
    FacturaResponse,
    ImpuestoDetalle,
    InfoFactura,
    Pago,
    ProductoItem,
    RecepcionResponse,
    TotalImpuesto,
)
from ..database import get_db
from ..models.db_models import Factura, Usuario
from .auth import get_current_user
from ..services.clave_acceso import generar_clave_acceso
from ..services.sri_client import consultar_autorizacion, enviar_comprobante
from ..services.xml_generator import generar_xml_factura
from ..services.xml_signer import firmar_xml

from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import func

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Facturación"])

# Precisión para cálculos monetarios (2 decimales, redondeo bancario)
DOS_DEC = Decimal("0.01")


def _siguiente_secuencial(db: Session) -> str:
    """Calcula el siguiente secuencial consultando la BD.

    Obtiene el máximo secuencial existente y le suma 1.
    Retorna string de 9 dígitos con zero-padding.
    """
    ultimo = db.query(func.max(Factura.secuencial)).scalar()
    if ultimo:
        siguiente = int(ultimo) + 1
    else:
        siguiente = 1
    return str(siguiente).zfill(9)


@router.get(
    "/facturar/secuencial",
    summary="Obtener el siguiente número secuencial",
    description="Consulta la base de datos y retorna el próximo secuencial disponible.",
)
def obtener_siguiente_secuencial(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Retorna el siguiente secuencial basado en el máximo de la BD."""
    return {"secuencial": _siguiente_secuencial(db)}


# ── Cálculos automáticos de impuestos ────────────────────


def _calcular_detalle(producto: ProductoItem) -> DetalleFactura:
    """Convierte un ProductoItem del JSON simplificado a DetalleFactura SRI.

    Calcula automáticamente:
      - precioTotalSinImpuesto = (cantidad × precioUnitario) − descuento
      - baseImponible = precioTotalSinImpuesto
      - valor del IVA = baseImponible × (tarifa / 100)
    """
    subtotal = (producto.cantidad * producto.precio_unitario) - producto.descuento
    subtotal = subtotal.quantize(DOS_DEC, rounding=ROUND_HALF_UP)

    tarifa = Decimal(TARIFA_IVA[producto.codigo_porcentaje_iva])
    valor_iva = (subtotal * tarifa / Decimal("100")).quantize(
        DOS_DEC, rounding=ROUND_HALF_UP
    )

    impuesto = ImpuestoDetalle(
        codigo=CodigoImpuesto.IVA,
        codigo_porcentaje=producto.codigo_porcentaje_iva,
        tarifa=tarifa,
        base_imponible=subtotal,
        valor=valor_iva,
    )

    return DetalleFactura(
        codigo_principal=producto.codigo,
        descripcion=producto.descripcion,
        cantidad=producto.cantidad,
        precio_unitario=producto.precio_unitario,
        descuento=producto.descuento,
        precio_total_sin_impuesto=subtotal,
        impuestos=[impuesto],
    )


def _calcular_totales_impuestos(
    detalles: list[DetalleFactura],
) -> list[TotalImpuesto]:
    """Agrupa los impuestos de todos los detalles por (código, códigoPorcentaje).

    Esto es lo que va en <totalConImpuestos> del XML.
    """
    agrupado: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(
        lambda: {"base_imponible": Decimal("0.00"), "valor": Decimal("0.00")}
    )

    for det in detalles:
        for imp in det.impuestos:
            key = (imp.codigo.value, imp.codigo_porcentaje.value)
            agrupado[key]["base_imponible"] += imp.base_imponible
            agrupado[key]["valor"] += imp.valor

    totales: list[TotalImpuesto] = []
    for (cod, cod_pct), valores in agrupado.items():
        totales.append(
            TotalImpuesto(
                codigo=CodigoImpuesto(cod),
                codigo_porcentaje=CodigoPorcentajeIVA(cod_pct),
                base_imponible=valores["base_imponible"].quantize(
                    DOS_DEC, rounding=ROUND_HALF_UP
                ),
                valor=valores["valor"].quantize(
                    DOS_DEC, rounding=ROUND_HALF_UP
                ),
            )
        )

    return totales


def _construir_factura_request(datos: FacturarRequest) -> FacturaRequest:
    """Transforma el JSON simplificado en el FacturaRequest completo del SRI.

    Este es el corazón de la orquestación: toma los datos de negocio
    y produce la estructura que espera el generador de XML.
    """
    # 1. Calcular cada detalle con sus impuestos
    detalles = [_calcular_detalle(p) for p in datos.productos]

    # 2. Totales
    total_sin_impuestos = sum(d.precio_total_sin_impuesto for d in detalles)
    total_descuento = sum(d.descuento for d in detalles)
    total_con_impuestos = _calcular_totales_impuestos(detalles)
    total_iva = sum(t.valor for t in total_con_impuestos)
    importe_total = (total_sin_impuestos + total_iva).quantize(
        DOS_DEC, rounding=ROUND_HALF_UP
    )

    # 3. InfoAdicional (inyectar email/teléfono del cliente si existen)
    info_adicional = dict(datos.info_adicional) if datos.info_adicional else {}
    if datos.cliente.email and "email" not in info_adicional:
        info_adicional["email"] = datos.cliente.email
    if datos.cliente.telefono and "telefono" not in info_adicional:
        info_adicional["telefono"] = datos.cliente.telefono

    # 4. Armar InfoFactura
    info_factura = InfoFactura(
        fecha_emision=datos.fecha_emision,
        tipo_identificacion_comprador=datos.cliente.tipo_identificacion,
        razon_social_comprador=datos.cliente.razon_social,
        identificacion_comprador=datos.cliente.identificacion,
        direccion_comprador=datos.cliente.direccion,
        total_sin_impuestos=total_sin_impuestos,
        total_descuento=total_descuento,
        total_con_impuestos=total_con_impuestos,
        importe_total=importe_total,
        pagos=[
            Pago(forma_pago=datos.forma_pago, total=importe_total)
        ],
    )

    return FacturaRequest(
        secuencial=datos.secuencial,
        info_factura=info_factura,
        detalles=detalles,
        info_adicional=info_adicional or None,
    )


# ── Endpoint principal ───────────────────────────────────


@router.post(
    "/facturar",
    response_model=FacturaResponse,
    summary="Facturar — flujo completo simplificado",
    description=(
        "Recibe un JSON con datos del cliente y productos/servicios. "
        "Calcula impuestos automáticamente y ejecuta el flujo completo: "
        "Generar XML → Firmar (XAdES-BES) → Enviar a Recepción SRI → "
        "Consultar Autorización SRI."
    ),
    responses={
        200: {"description": "Factura procesada (ver estado de autorización)"},
        400: {"description": "Error de validación en los datos de entrada"},
        500: {"description": "Error interno (firma, configuración)"},
        502: {"description": "Error de comunicación con el SRI"},
    },
)
def facturar(
    datos: FacturarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    incluir_xml: bool = Query(
        False,
        description="Si es True, incluye el XML firmado en base64 en la respuesta",
    ),
):
    """Ejecuta el flujo completo de facturación electrónica.

    Pasos internos:
      1. Calcular impuestos y totales a partir de los productos.
      2. Generar clave de acceso de 49 dígitos (Módulo 11).
      3. Generar XML de factura v1.1.0 conforme al SRI.
      4. Firmar con XAdES-BES (.p12).
      4.5 Guardar factura en SQLite.
      5. Enviar a RecepcionComprobantesOffline.
      6. Consultar AutorizacionComprobantesOffline.
      7. Actualizar estado SRI en la BD.
    """
    # ── Paso 0: Calcular secuencial real desde la BD ───────
    secuencial_real = _siguiente_secuencial(db)
    datos = datos.model_copy(update={"secuencial": secuencial_real})

    # ── Paso 1: Transformar JSON simplificado → FacturaRequest SRI ──
    try:
        factura = _construir_factura_request(datos)
    except Exception as e:
        logger.exception("Error al construir la factura")
        raise HTTPException(
            status_code=400,
            detail=f"Error al calcular impuestos/totales: {e}",
        )

    # ── Paso 2: Generar clave de acceso ──────────────────
    try:
        clave_acceso = generar_clave_acceso(
            fecha_emision=factura.info_factura.fecha_emision,
            tipo_comprobante=TipoDocumento.FACTURA.value,
            ruc=settings.EMISOR_RUC,
            ambiente=settings.SRI_AMBIENTE,
            establecimiento=settings.EMISOR_ESTABLECIMIENTO,
            punto_emision=settings.EMISOR_PUNTO_EMISION,
            secuencial=factura.secuencial,
            tipo_emision=settings.SRI_TIPO_EMISION,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error en clave de acceso: {e}",
        )

    logger.info(
        "Clave de acceso generada: %s (secuencial: %s)",
        clave_acceso,
        factura.secuencial,
    )

    # ── Paso 3: Generar XML ──────────────────────────────
    xml_sin_firmar = generar_xml_factura(factura, clave_acceso)
    logger.info("XML generado (%d bytes)", len(xml_sin_firmar))

    # ── Paso 4: Firmar XML (XAdES-BES) ───────────────────
    try:
        xml_firmado = firmar_xml(xml_sin_firmar)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Archivo de firma electrónica (.p12) no encontrado. "
                "Verifique que exista en la carpeta certificados/."
            ),
        )
    except Exception as e:
        logger.exception("Error al firmar XML")
        raise HTTPException(
            status_code=500,
            detail=f"Error al firmar el comprobante: {e}",
        )

    logger.info("XML firmado (%d bytes)", len(xml_firmado))

    # ── Paso 4.5: Guardar factura en SQLite ───────────────
    ec_tz = ZoneInfo("America/Guayaquil")
    hora_ecuador = datetime.now(ec_tz).replace(tzinfo=None)

    factura_db = Factura(
        secuencial=factura.secuencial,
        fecha_emision=factura.info_factura.fecha_emision,
        identificacion_cliente=factura.info_factura.identificacion_comprador,
        total=float(factura.info_factura.importe_total),
        clave_acceso=clave_acceso,
        estado_sri="SIMULADO",
        xml_generado=xml_firmado.decode("utf-8"),
        usuario_id=current_user.id,
        created_at=hora_ecuador,
        sede=datos.sede or "gym",
    )
    db.add(factura_db)
    db.commit()
    db.refresh(factura_db)
    logger.info(
        "Factura guardada en BD (id=%d, clave=%s)",
        factura_db.id,
        clave_acceso,
    )

    # ── Paso 5: Enviar a RecepcionComprobantesOffline ─────
    try:
        recepcion: RecepcionResponse = enviar_comprobante(xml_firmado)
        recepcion.clave_acceso = clave_acceso
    except ConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo conectar al WS de recepción del SRI: {e}",
        )
    except Exception as e:
        logger.exception("Error al enviar comprobante al SRI")
        raise HTTPException(
            status_code=502,
            detail=f"Error de comunicación con el SRI (recepción): {e}",
        )

    logger.info("Recepción SRI → estado: %s", recepcion.estado)

    # ── Paso 6: Consultar AutorizacionComprobantesOffline ─
    autorizacion = None
    if recepcion.estado == "RECIBIDA":
        try:
            autorizacion = consultar_autorizacion(clave_acceso)
            logger.info(
                "Autorización SRI → estado: %s",
                autorizacion.estado if autorizacion else "N/A",
            )
        except ConnectionError as e:
            logger.warning(
                "No se pudo consultar autorización: %s", e
            )
        except Exception as e:
            logger.warning("Error al consultar autorización: %s", e)

    # ── Paso 7: Actualizar estado SRI en la BD ───────────
    estado_final = "SIMULADO"
    if autorizacion:
        estado_final = autorizacion.estado
    elif recepcion.estado:
        estado_final = recepcion.estado

    factura_db.estado_sri = estado_final
    db.commit()
    logger.info("Estado SRI actualizado en BD: %s", estado_final)

    # ── Paso 8: Armar respuesta ──────────────────────────
    xml_b64 = None
    if incluir_xml:
        xml_b64 = base64.b64encode(xml_firmado).decode("utf-8")

    return FacturaResponse(
        id=factura_db.id,
        clave_acceso=clave_acceso,
        secuencial=factura.secuencial,
        fecha_emision=factura.info_factura.fecha_emision,
        recepcion=recepcion,
        autorizacion=autorizacion,
        xml_firmado=xml_b64,
    )
