"""
Endpoints REST para el módulo de facturación electrónica.

Incluye:
  - POST /facturas          → Emitir factura (estructura SRI completa).
  - GET  /facturas          → Historial de facturas (SQLite).
  - GET  /facturas/{id}/pdf → Descargar RIDE en PDF.
  - GET  /facturas/autorizacion/{clave} → Consultar autorización SRI.
"""

import base64
import logging
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.db_models import Cliente, Factura, Usuario
from .auth import get_current_user
from ..models.enums import TipoDocumento
from ..models.schemas import (
    AutorizacionResponse,
    DetalleHistorialItem,
    FacturaHistorialItem,
    FacturaRequest,
    FacturaResponse,
    RecepcionResponse,
)
from ..services.clave_acceso import generar_clave_acceso
from ..services.pdf_generator import generar_ride_pdf
from ..services.sri_client import consultar_autorizacion, enviar_comprobante
from ..services.xml_generator import generar_xml_factura
from ..services.xml_signer import firmar_xml

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facturas", tags=["Facturas"])


def _extraer_detalles_xml(xml_str: str) -> list[DetalleHistorialItem]:
    """Extrae los productos/servicios del XML almacenado de la factura."""
    detalles = []
    try:
        root = ET.fromstring(xml_str)
        for det in root.iter("detalle"):
            desc = det.findtext("descripcion", "")
            cant = float(det.findtext("cantidad", "1"))
            precio = float(det.findtext("precioUnitario", "0"))
            subtotal = float(det.findtext("precioTotalSinImpuesto", "0"))
            detalles.append(DetalleHistorialItem(
                descripcion=desc, cantidad=cant,
                precio_unitario=precio, subtotal=subtotal,
            ))
    except Exception:
        pass
    return detalles


# ── POST /facturas — Emitir factura (estructura SRI completa) ─


@router.post(
    "",
    response_model=FacturaResponse,
    summary="Emitir factura electrónica",
    description=(
        "Genera, firma y envía una factura electrónica al SRI. "
        "Retorna la clave de acceso y el resultado de recepción/autorización."
    ),
)
def emitir_factura(
    factura: FacturaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    incluir_xml: bool = Query(
        False,
        description="Si es True, incluye el XML firmado en base64 en la respuesta",
    ),
):
    # 1. Generar clave de acceso
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
        raise HTTPException(status_code=400, detail=f"Error en clave de acceso: {e}")

    # 2. Generar XML
    xml_sin_firmar = generar_xml_factura(factura, clave_acceso)

    # 3. Firmar XML
    try:
        xml_firmado = firmar_xml(xml_sin_firmar)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Archivo de firma electrónica (.p12) no encontrado. Verifique la configuración.",
        )
    except Exception as e:
        logger.exception("Error al firmar XML")
        raise HTTPException(
            status_code=500,
            detail=f"Error al firmar el comprobante: {e}",
        )

    # 4. Enviar al SRI
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

    # 5. Consultar autorización (solo si la recepción fue exitosa)
    autorizacion = None
    if recepcion.estado == "RECIBIDA":
        try:
            autorizacion = consultar_autorizacion(clave_acceso)
        except Exception as e:
            logger.warning("Error al consultar autorización: %s", e)

    # 6. Armar respuesta
    xml_b64 = None
    if incluir_xml:
        xml_b64 = base64.b64encode(xml_firmado).decode("utf-8")

    return FacturaResponse(
        clave_acceso=clave_acceso,
        secuencial=factura.secuencial,
        fecha_emision=factura.info_factura.fecha_emision,
        recepcion=recepcion,
        autorizacion=autorizacion,
        xml_firmado=xml_b64,
    )


# ── GET /facturas — Historial de facturas ────────────────


@router.get(
    "",
    response_model=list[FacturaHistorialItem],
    summary="Historial de facturas emitidas",
    description=(
        "Devuelve todas las facturas registradas en la base de datos local, "
        "ordenadas de la más reciente a la más antigua."
    ),
)
def listar_facturas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    limite: int = Query(
        100,
        ge=1,
        le=1000,
        description="Cantidad máxima de facturas a retornar",
    ),
    estado: str | None = Query(
        None,
        description="Filtrar por estado SRI (ej: SIMULADO, DEVUELTA, AUTORIZADO)",
    ),
    sede: str | None = Query(
        None,
        description="Filtrar por sede (gym o box)",
    ),
):
    """Lista el historial de facturas. Admin ve todas, vendedor solo las suyas."""
    query = db.query(Factura, Cliente.telefono, Usuario.nombre_completo).outerjoin(
        Cliente, Factura.identificacion_cliente == Cliente.cedula_ruc
    ).outerjoin(
        Usuario, Factura.usuario_id == Usuario.id
    )

    if estado:
        query = query.filter(Factura.estado_sri == estado.upper())

    if sede:
        query = query.filter(Factura.sede == sede)

    # Filtrar por rol: vendedor solo ve sus facturas
    if current_user.rol != "admin":
        query = query.filter(Factura.usuario_id == current_user.id)

    filas = (
        query.order_by(Factura.created_at.desc())
        .limit(limite)
        .all()
    )

    resultado = []
    for f, tel_cliente, vendedor_nombre in filas:
        item = FacturaHistorialItem(
            id=f.id,
            secuencial=f.secuencial,
            fecha_emision=f.fecha_emision,
            identificacion_cliente=f.identificacion_cliente,
            total=float(f.total),
            clave_acceso=f.clave_acceso,
            estado_sri=f.estado_sri,
            telefono_cliente=tel_cliente,
            vendedor_nombre=vendedor_nombre,
            created_at=f.created_at.strftime("%d/%m/%Y %H:%M:%S") if f.created_at else None,
            detalles=_extraer_detalles_xml(f.xml_generado) if f.xml_generado else [],
            sede=f.sede,
        )
        resultado.append(item)

    logger.info("Historial consultado: %d facturas retornadas", len(resultado))
    return resultado


# ── GET /facturas/cliente/{cedula} — Historial por cliente ─


@router.get(
    "/cliente/{cedula}",
    response_model=list[FacturaHistorialItem],
    summary="Historial de compras de un cliente",
    description="Devuelve todas las facturas asociadas a una cédula/RUC, ordenadas de la más reciente a la más antigua.",
)
def historial_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    filas = (
        db.query(Factura, Cliente.telefono, Usuario.nombre_completo)
        .outerjoin(Cliente, Factura.identificacion_cliente == Cliente.cedula_ruc)
        .outerjoin(Usuario, Factura.usuario_id == Usuario.id)
        .filter(Factura.identificacion_cliente == cedula)
        .order_by(Factura.created_at.desc())
        .all()
    )

    return [
        FacturaHistorialItem(
            id=f.id,
            secuencial=f.secuencial,
            fecha_emision=f.fecha_emision,
            identificacion_cliente=f.identificacion_cliente,
            total=float(f.total),
            clave_acceso=f.clave_acceso,
            estado_sri=f.estado_sri,
            telefono_cliente=tel,
            vendedor_nombre=vendedor,
            created_at=f.created_at.strftime("%d/%m/%Y %H:%M:%S") if f.created_at else None,
            detalles=_extraer_detalles_xml(f.xml_generado) if f.xml_generado else [],
            sede=f.sede,
        )
        for f, tel, vendedor in filas
    ]


# ── GET /facturas/{id}/pdf — Descargar RIDE en PDF ───────


@router.get(
    "/{id_factura}/pdf",
    summary="Descargar RIDE (PDF)",
    description=(
        "Genera y descarga el RIDE (Representación Impresa del Documento Electrónico) "
        "en formato PDF para la factura indicada. Ideal para enviar por WhatsApp."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Archivo PDF del RIDE",
        },
        404: {"description": "Factura no encontrada"},
    },
)
def descargar_ride_pdf(
    id_factura: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Busca la factura en SQLite, genera el PDF del RIDE y lo retorna como descarga."""
    factura = db.query(Factura).filter(Factura.id == id_factura).first()

    if not factura:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró una factura con ID {id_factura}.",
        )

    # Obtener nombre del cliente
    cliente = db.query(Cliente).filter(Cliente.cedula_ruc == factura.identificacion_cliente).first()
    nombre_cliente = cliente.nombre_completo if cliente else None

    # Generar PDF
    try:
        pdf_bytes = generar_ride_pdf(factura, nombre_cliente=nombre_cliente)
    except Exception as e:
        logger.exception("Error al generar RIDE PDF para factura id=%d", id_factura)
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el PDF del RIDE: {e}",
        )

    # Nombre del archivo para la descarga
    nombre_archivo = (
        f"RIDE_{settings.EMISOR_ESTABLECIMIENTO}-"
        f"{settings.EMISOR_PUNTO_EMISION}-"
        f"{factura.secuencial}.pdf"
    )

    logger.info(
        "RIDE descargado — factura id=%d, archivo=%s",
        id_factura,
        nombre_archivo,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{nombre_archivo}"',
        },
    )


# ── GET /facturas/autorizacion/{clave} — Consulta SRI ────


@router.get(
    "/autorizacion/{clave_acceso}",
    response_model=AutorizacionResponse,
    summary="Consultar autorización de comprobante",
    description="Consulta el estado de autorización de un comprobante ya enviado al SRI.",
)
def obtener_autorizacion(clave_acceso: str, current_user: Usuario = Depends(get_current_user)):
    if len(clave_acceso) != 49 or not clave_acceso.isdigit():
        raise HTTPException(
            status_code=400,
            detail="La clave de acceso debe tener exactamente 49 dígitos numéricos.",
        )

    try:
        return consultar_autorizacion(clave_acceso)
    except ConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo conectar al WS de autorización del SRI: {e}",
        )
    except Exception as e:
        logger.exception("Error al consultar autorización")
        raise HTTPException(
            status_code=502,
            detail=f"Error de comunicación con el SRI (autorización): {e}",
        )
