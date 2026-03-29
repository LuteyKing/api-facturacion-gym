"""
Endpoints de autenticación y dependencias de seguridad.

Incluye:
  - POST /auth/token  → Login (OAuth2 + JWT)
  - GET  /auth/me     → Perfil del usuario actual
  - Dependencia get_current_user para proteger rutas
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.db_models import Usuario

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ── Hashing de contraseñas ───────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 — apunta al endpoint de login ─────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# ── Schemas de respuesta ─────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str


class UsuarioOut(BaseModel):
    id: int
    username: str
    nombre_completo: str
    rol: str

    class Config:
        from_attributes = True


# ── Utilidades ────────────────────────────────────────────

def verificar_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def crear_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Dependencia: obtener usuario actual ──────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Decodifica el JWT y retorna el Usuario de la BD."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Dependencia que exige rol 'admin'."""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return current_user


# ── POST /auth/token — Login ─────────────────────────────

@router.post("/token", response_model=Token, summary="Iniciar sesión")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Autentica al usuario y retorna un JWT."""
    user = db.query(Usuario).filter(Usuario.username == form_data.username).first()
    if not user or not verificar_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = crear_token({"sub": user.username, "rol": user.rol})
    logger.info("Login exitoso: %s (rol: %s)", user.username, user.rol)
    return Token(access_token=token, token_type="bearer")


# ── GET /auth/me — Perfil del usuario actual ─────────────

@router.get("/me", response_model=UsuarioOut, summary="Perfil del usuario autenticado")
def perfil(current_user: Usuario = Depends(get_current_user)):
    return UsuarioOut(
        id=current_user.id,
        username=current_user.username,
        nombre_completo=current_user.nombre_completo,
        rol=current_user.rol,
    )
