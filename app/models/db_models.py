from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


# --- TABLA: USUARIOS ---
class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="vendedor")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    usuario_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=True)
    sede: Mapped[str] = mapped_column(String(10), nullable=False, server_default="gym", index=True)

# --- NUEVA TABLA: CLIENTES (ALUMNOS) ---
class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cedula_ruc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    sede: Mapped[str] = mapped_column(String(10), nullable=False, server_default="gym", index=True)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


# --- TABLA: CONFIGURACIÓN DINÁMICA ---
class Configuracion(Base):
    __tablename__ = "configuracion"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    logo_gym_url: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    logo_box_url: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    favicon_url: Mapped[str] = mapped_column(Text, nullable=False, server_default="")


# --- NUEVA TABLA: PRODUCTOS (SERVICIOS) ---
class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    iva_aplica: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    sede: Mapped[str] = mapped_column(String(10), nullable=False, server_default="gym", index=True)