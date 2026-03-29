"""
Endpoints REST para gestión de usuarios (solo administradores).

Incluye:
  - GET    /usuarios              → Listar todos los usuarios.
  - POST   /usuarios              → Crear nuevo usuario.
  - PUT    /usuarios/{id}/password → Cambiar contraseña de un usuario.
  - DELETE /usuarios/{id}          → Eliminar un usuario.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Usuario
from .auth import get_current_user, hash_password, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


# ── Schemas ──────────────────────────────────────────────

class UsuarioCreate(BaseModel):
    username: str
    password: str
    nombre_completo: str
    rol: str = "vendedor"


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre_completo: str
    rol: str

    class Config:
        from_attributes = True


class CambiarPassword(BaseModel):
    nueva_password: str


# ── GET /usuarios — Listar usuarios ─────────────────────

@router.get("", response_model=list[UsuarioOut], summary="Listar todos los usuarios")
def listar_usuarios(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
):
    usuarios = db.query(Usuario).order_by(Usuario.id).all()
    logger.info("Usuarios listados: %d registros (por %s)", len(usuarios), admin.username)
    return usuarios


# ── POST /usuarios — Crear usuario ──────────────────────

@router.post("", response_model=UsuarioOut, summary="Crear nuevo usuario")
def crear_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
):
    if datos.rol not in ("admin", "vendedor"):
        raise HTTPException(status_code=400, detail="El rol debe ser 'admin' o 'vendedor'")

    existente = db.query(Usuario).filter(Usuario.username == datos.username).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un usuario con username: {datos.username}")

    nuevo = Usuario(
        username=datos.username,
        password_hash=hash_password(datos.password),
        nombre_completo=datos.nombre_completo,
        rol=datos.rol,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    logger.info("Usuario creado: %s (rol: %s) por %s", nuevo.username, nuevo.rol, admin.username)
    return nuevo


# ── PUT /usuarios/{id}/password — Cambiar contraseña ────

@router.put("/{usuario_id}/password", summary="Cambiar contraseña de un usuario")
def cambiar_password(
    usuario_id: int,
    datos: CambiarPassword,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.password_hash = hash_password(datos.nueva_password)
    db.commit()

    logger.info("Contraseña cambiada para '%s' por admin '%s'", usuario.username, admin.username)
    return {"detail": f"Contraseña de '{usuario.username}' actualizada correctamente"}


# ── DELETE /usuarios/{id} — Eliminar usuario ────────────

@router.delete("/{usuario_id}", summary="Eliminar un usuario")
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    username = usuario.username
    db.delete(usuario)
    db.commit()

    logger.info("Usuario '%s' eliminado por admin '%s'", username, admin.username)
    return {"detail": f"Usuario '{username}' eliminado correctamente"}
