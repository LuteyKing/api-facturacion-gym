"""
Modelos SQLAlchemy para persistencia local de facturas.

Tabla `facturas`:
  Almacena el historial de cada comprobante emitido,
  incluyendo el XML generado y el estado devuelto por el SRI
  (o "SIMULADO" cuando se usa el mock de firma).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Factura(Base):
    """Registro persistente de una factura electrónica emitida."""

    __tablename__ = "facturas"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Identificador único interno",
    )

    secuencial: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
        index=True,
        comment="Secuencial de 9 dígitos (ej: 000000001)",
    )

    fecha_emision: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Fecha de emisión dd/mm/yyyy",
    )

    identificacion_cliente: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="RUC, cédula o pasaporte del comprador",
    )

    total: Mapped[float] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
        comment="Importe total de la factura",
    )

    clave_acceso: Mapped[str] = mapped_column(
        String(49),
        nullable=False,
        unique=True,
        index=True,
        comment="Clave de acceso de 49 dígitos (Módulo 11)",
    )

    estado_sri: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SIMULADO",
        server_default="SIMULADO",
        comment="Estado del SRI: SIMULADO | RECIBIDA | AUTORIZADO | NO AUTORIZADO",
    )

    xml_generado: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="XML completo del comprobante (sin firmar en modo simulación)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Fecha y hora de creación del registro",
    )

    def __repr__(self) -> str:
        return (
            f"<Factura(id={self.id}, sec={self.secuencial}, "
            f"cliente={self.identificacion_cliente}, "
            f"estado={self.estado_sri})>"
        )
