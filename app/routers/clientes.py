"""
Endpoints REST para gestión de clientes (alumnos del gimnasio).

Incluye:
  - POST /clientes          → Registrar nuevo cliente.
  - GET  /clientes          → Listar todos los clientes.
  - GET  /clientes/{cedula} → Buscar cliente por cédula/RUC.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Cliente, Usuario
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clientes", tags=["Clientes"])


# ── Esquema Pydantic ─────────────────────────────────────
class ClienteCreate(BaseModel):
    cedula_ruc: str
    nombre_completo: str
    correo: str | None = None
    telefono: str | None = None
    direccion: str | None = None


class ClienteResponse(BaseModel):
    id: int
    cedula_ruc: str
    nombre_completo: str
    correo: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


# ── POST /clientes — Registrar cliente ───────────────────
@router.post("", response_model=ClienteResponse, summary="Registrar nuevo cliente")
def crear_cliente(cliente: ClienteCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Registra un nuevo cliente/alumno en la base de datos."""
    # Verificar si ya existe
    existente = db.query(Cliente).filter(Cliente.cedula_ruc == cliente.cedula_ruc).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un cliente con cédula/RUC: {cliente.cedula_ruc}"
        )

    db_cliente = Cliente(
        cedula_ruc=cliente.cedula_ruc,
        nombre_completo=cliente.nombre_completo,
        correo=cliente.correo,
        telefono=cliente.telefono,
        direccion=cliente.direccion,
        created_at=datetime.now(ZoneInfo("America/Guayaquil")).replace(tzinfo=None),
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)

    logger.info("Cliente registrado: %s — %s", db_cliente.cedula_ruc, db_cliente.nombre_completo)

    return ClienteResponse(
        id=db_cliente.id,
        cedula_ruc=db_cliente.cedula_ruc,
        nombre_completo=db_cliente.nombre_completo,
        correo=db_cliente.correo,
        telefono=db_cliente.telefono,
        direccion=db_cliente.direccion,
        created_at=db_cliente.created_at.strftime("%d/%m/%Y %H:%M:%S") if db_cliente.created_at else None,
    )


# ── GET /clientes — Listar clientes ─────────────────────
@router.get("", response_model=list[ClienteResponse], summary="Listar todos los clientes")
def listar_clientes(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Retorna todos los clientes registrados, ordenados del más reciente al más antiguo."""
    clientes = db.query(Cliente).order_by(Cliente.created_at.desc()).all()

    resultado = []
    for c in clientes:
        resultado.append(ClienteResponse(
            id=c.id,
            cedula_ruc=c.cedula_ruc,
            nombre_completo=c.nombre_completo,
            correo=c.correo,
            telefono=c.telefono,
            direccion=c.direccion,
            created_at=c.created_at.strftime("%d/%m/%Y %H:%M:%S") if c.created_at else None,
        ))

    logger.info("Clientes consultados: %d registros", len(resultado))
    return resultado


# ── GET /clientes/{cedula} — Buscar por cédula ──────────
@router.get("/{cedula}", response_model=ClienteResponse, summary="Buscar cliente por cédula/RUC")
def obtener_cliente(cedula: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Busca un cliente específico por su número de cédula o RUC."""
    cliente = db.query(Cliente).filter(Cliente.cedula_ruc == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    return ClienteResponse(
        id=cliente.id,
        cedula_ruc=cliente.cedula_ruc,
        nombre_completo=cliente.nombre_completo,
        correo=cliente.correo,
        telefono=cliente.telefono,
        direccion=cliente.direccion,
        created_at=cliente.created_at.strftime("%d/%m/%Y %H:%M:%S") if cliente.created_at else None,
    )