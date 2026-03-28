"""Modelos Pydantic que mapean la estructura XML del SRI para facturas."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import (
    CodigoImpuesto,
    CodigoPorcentajeIVA,
    FormaPago,
    TARIFA_IVA,
    TipoIdentificacion,
)


# ── Impuestos a nivel de detalle ─────────────────────────


class ImpuestoDetalle(BaseModel):
    """Impuesto aplicado a un ítem de la factura."""

    codigo: CodigoImpuesto = Field(
        default=CodigoImpuesto.IVA,
        description="Código del tipo de impuesto (2=IVA, 3=ICE, 5=IRBPNR)",
    )
    codigo_porcentaje: CodigoPorcentajeIVA = Field(
        ...,
        description="Código del porcentaje del impuesto según tabla SRI",
    )
    tarifa: Decimal = Field(
        ...,
        description="Porcentaje de tarifa del impuesto (ej: 15.00)",
    )
    base_imponible: Decimal = Field(
        ..., ge=0, description="Base imponible del ítem"
    )
    valor: Decimal = Field(
        ..., ge=0, description="Valor del impuesto calculado"
    )


# ── Detalle (línea de la factura) ────────────────────────


class DetalleFactura(BaseModel):
    """Línea individual de la factura (producto o servicio)."""

    codigo_principal: str = Field(
        ..., max_length=25, description="Código interno del producto/servicio"
    )
    codigo_auxiliar: Optional[str] = Field(
        None, max_length=25, description="Código auxiliar opcional"
    )
    descripcion: str = Field(
        ..., max_length=300, description="Descripción del servicio/producto"
    )
    cantidad: Decimal = Field(..., gt=0)
    precio_unitario: Decimal = Field(..., ge=0)
    descuento: Decimal = Field(default=Decimal("0.00"), ge=0)
    precio_total_sin_impuesto: Decimal = Field(..., ge=0)
    impuestos: list[ImpuestoDetalle] = Field(
        ...,
        min_length=1,
        description=(
            "Obligatorio: al menos un impuesto por ítem (Ítem IVA 0% inclusive). "
            "SRI rechaza detalles sin el sub-nodo <impuestos>."
        ),
    )


# ── Totales de impuestos ─────────────────────────────────


class TotalImpuesto(BaseModel):
    codigo: CodigoImpuesto = Field(default=CodigoImpuesto.IVA)
    codigo_porcentaje: CodigoPorcentajeIVA
    descuento_adicional: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible: Decimal = Field(..., ge=0)
    valor: Decimal = Field(..., ge=0)


# ── Pago ─────────────────────────────────────────────────


class Pago(BaseModel):
    forma_pago: FormaPago
    total: Decimal = Field(..., ge=0)
    plazo: Optional[int] = Field(None, ge=0)
    unidad_tiempo: Optional[str] = Field(None, description="dias, meses, etc.")


# ── Información de la factura ────────────────────────────


class InfoFactura(BaseModel):
    fecha_emision: str = Field(
        ...,
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Fecha de emisión dd/mm/yyyy",
    )
    dir_establecimiento: Optional[str] = Field(None, max_length=300)
    obligado_contabilidad: str = Field(default="NO", pattern=r"^(SI|NO)$")
    contribuyente_especial: Optional[str] = None
    tipo_identificacion_comprador: TipoIdentificacion = Field(
        ...,
        description=(
            "Obligatorio según Ficha Técnica SRI. "
            "04=RUC, 05=Cédula, 06=Pasaporte, 07=Consumidor Final, 08=Exterior"
        ),
    )
    razon_social_comprador: str = Field(..., max_length=300)
    identificacion_comprador: str = Field(..., max_length=20)
    direccion_comprador: Optional[str] = Field(None, max_length=300)
    total_sin_impuestos: Decimal = Field(..., ge=0)
    total_descuento: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_con_impuestos: list[TotalImpuesto] = Field(
        ...,
        min_length=1,
        description=(
            "Obligatorio: totales agrupados por código de impuesto y código de porcentaje. "
            "Debe existir al menos un totalImpuesto (ej: IVA 0%)."
        ),
    )
    propina: Decimal = Field(default=Decimal("0.00"), ge=0)
    importe_total: Decimal = Field(..., ge=0)
    moneda: str = Field(default="DOLAR")
    pagos: list[Pago] = Field(..., min_length=1)

    @field_validator("identificacion_comprador")
    @classmethod
    def validar_identificacion(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La identificación del comprador no puede estar vacía")
        return v.strip()

    @field_validator("identificacion_comprador")
    @classmethod
    def validar_longitud_identificacion(
        cls, v: str, info
    ) -> str:
        """Valida longitud según tipo de identificación."""
        tipo = info.data.get("tipo_identificacion_comprador")
        v = v.strip()
        if tipo == TipoIdentificacion.RUC and len(v) != 13:
            raise ValueError("El RUC debe tener exactamente 13 dígitos")
        if tipo == TipoIdentificacion.CEDULA and len(v) != 10:
            raise ValueError("La cédula debe tener exactamente 10 dígitos")
        if tipo == TipoIdentificacion.CONSUMIDOR_FINAL and v != "9999999999999":
            raise ValueError(
                "Para consumidor final la identificación debe ser 9999999999999"
            )
        return v


# ── Request completo para crear factura ──────────────────


class FacturaRequest(BaseModel):
    """Payload que el cliente envía al endpoint POST /facturas."""

    secuencial: str = Field(
        ...,
        min_length=9,
        max_length=9,
        pattern=r"^\d{9}$",
        description="Número secuencial de 9 dígitos",
    )
    info_factura: InfoFactura
    detalles: list[DetalleFactura] = Field(
        ...,
        min_length=1,
        description="Al menos un detalle requerido. Cada detalle DEBE incluir <impuestos>.",
    )
    info_adicional: Optional[dict[str, str]] = Field(
        None,
        description=(
            "Campos adicionales opcionales del comprobante. Ej: "
            '{"email": "cliente@mail.com", "telefono": "0991234567"}'
        ),
    )

    @model_validator(mode="after")
    def validar_consistencia_totales(self) -> "FacturaRequest":
        """Verifica que totalSinImpuestos coincida con la suma de los detalles."""
        suma_detalles = sum(d.precio_total_sin_impuesto for d in self.detalles)
        esperado = self.info_factura.total_sin_impuestos
        if abs(suma_detalles - esperado) > Decimal("0.01"):
            raise ValueError(
                f"totalSinImpuestos ({esperado}) no coincide con la suma "
                f"de precioTotalSinImpuesto de los detalles ({suma_detalles})"
            )
        return self


# ── Respuestas ───────────────────────────────────────────


class MensajeSRI(BaseModel):
    identificador: str
    mensaje: str
    tipo: str
    informacion_adicional: Optional[str] = None


class RecepcionResponse(BaseModel):
    estado: str
    clave_acceso: str
    mensajes: list[MensajeSRI] = []


class AutorizacionResponse(BaseModel):
    estado: str
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[str] = None
    clave_acceso: str
    comprobante: Optional[str] = None
    mensajes: list[MensajeSRI] = []


class FacturaResponse(BaseModel):
    """Respuesta unificada al emitir una factura."""

    id: Optional[int] = Field(
        None, description="ID interno de la factura en la base de datos"
    )
    clave_acceso: str
    secuencial: str
    fecha_emision: str
    recepcion: RecepcionResponse
    autorizacion: Optional[AutorizacionResponse] = None
    xml_firmado: Optional[str] = Field(
        None, description="XML firmado en base64 (solo si se solicita)"
    )


class FacturaHistorialItem(BaseModel):
    """Registro de factura almacenado en la base de datos local."""

    id: int
    secuencial: str
    fecha_emision: str
    identificacion_cliente: str
    total: float
    clave_acceso: str
    estado_sri: str
    created_at: Optional[str] = Field(
        None, description="Fecha y hora de creación del registro (UTC)"
    )

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════
# MODELOS SIMPLIFICADOS — Endpoint POST /api/v1/facturar
# ═══════════════════════════════════════════════════════════
# JSON orientado al negocio: el frontend envía datos del cliente
# y la lista de productos/servicios con precio + código IVA.
# La API calcula automáticamente los impuestos, totales y arma
# el FacturaRequest interno que cumple con el esquema del SRI.
# ═══════════════════════════════════════════════════════════


class ProductoItem(BaseModel):
    """Producto o servicio vendido."""

    codigo: str = Field(
        ...,
        max_length=25,
        description="Código interno del producto/servicio",
        examples=["PROD-001", "SERV-010", "INV-100"],
    )
    descripcion: str = Field(
        ...,
        max_length=300,
        description="Nombre/descripción del servicio",
        examples=[
            "Servicio Profesional A",
            "Producto de Prueba B",
            "Consultoría mensual",
        ],
    )
    cantidad: Decimal = Field(..., gt=0, examples=[1])
    precio_unitario: Decimal = Field(..., ge=0, examples=["35.00"])
    descuento: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Descuento monetario sobre el ítem",
    )
    codigo_porcentaje_iva: CodigoPorcentajeIVA = Field(
        default=CodigoPorcentajeIVA.IVA_15,
        description=(
            "Código de porcentaje IVA según tabla SRI: "
            "0=0%, 2=12%, 3=14%, 4=15%, 5=5%, 6=No objeto, 7=Exento"
        ),
    )


class ClienteFactura(BaseModel):
    """Datos del comprador."""

    tipo_identificacion: TipoIdentificacion = Field(
        ...,
        description="04=RUC, 05=Cédula, 06=Pasaporte, 07=Consumidor Final",
    )
    identificacion: str = Field(
        ..., max_length=20, description="Número de RUC, cédula o pasaporte"
    )
    razon_social: str = Field(
        ..., max_length=300, description="Nombre completo o razón social"
    )
    direccion: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=300)
    telefono: Optional[str] = Field(None, max_length=20)


class FacturarRequest(BaseModel):
    """
    JSON simplificado para el endpoint POST /api/v1/facturar.

    El frontend envía solo los datos del cliente, el secuencial,
    la forma de pago y la lista de productos. La API se encarga
    de calcular impuestos, totales y armar el XML del SRI.

    Ejemplo mínimo:
    ```json
    {
      "secuencial": "000000001",
      "fecha_emision": "26/03/2026",
      "cliente": {
        "tipo_identificacion": "05",
        "identificacion": "0102030405",
        "razon_social": "Juan Pérez"
      },
      "productos": [
        {
          "codigo": "SERV-001",
          "descripcion": "Servicio Profesional",
          "cantidad": 1,
          "precio_unitario": "35.00"
        }
      ],
      "forma_pago": "01"
    }
    ```
    """

    secuencial: str = Field(
        ...,
        min_length=9,
        max_length=9,
        pattern=r"^\d{9}$",
        description="Número secuencial de 9 dígitos",
    )
    fecha_emision: str = Field(
        ...,
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Fecha de emisión dd/mm/yyyy",
        examples=["26/03/2026"],
    )
    cliente: ClienteFactura
    productos: list[ProductoItem] = Field(..., min_length=1)
    forma_pago: FormaPago = Field(
        default=FormaPago.SIN_SISTEMA_FINANCIERO,
        description="Forma de pago (01=Efectivo, 16=T.Débito, 19=T.Crédito, …)",
    )
    info_adicional: Optional[dict[str, str]] = Field(
        None,
        description="Campos adicionales opcionales (email, teléfono, etc.)",
    )