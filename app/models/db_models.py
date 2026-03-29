from datetime import datetime, timezone
from sqlalchemy import DateTime, Numeric, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class Factura(Base):
    __tablename__ = "facturas"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    secuencial: Mapped[str] = mapped_column(String(9), nullable=False, index=True)
    fecha_emision: Mapped[str] = mapped_column(String(10), nullable=False)
    identificacion_cliente: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    clave_acceso: Mapped[str] = mapped_column(String(49), nullable=False, unique=True, index=True)
    estado_sri: Mapped[str] = mapped_column(String(30), nullable=False, default="SIMULADO")
    xml_generado: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

# --- NUEVA TABLA: CLIENTES (ALUMNOS) ---
class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cedula_ruc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# --- NUEVA TABLA: PRODUCTOS (SERVICIOS) ---
class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    iva_aplica: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))