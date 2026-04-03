"""
Endpoints REST para configuración dinámica (logos, favicon).

  - GET  /configuracion     → Obtener la configuración actual (público)
  - PUT  /configuracion     → Actualizar configuración (solo admin)
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Configuracion
from .auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/configuracion", tags=["Configuración"])


# ── Schemas ──────────────────────────────────────────────

class ConfiguracionOut(BaseModel):
    id: int
    logo_gym_url: str
    logo_box_url: str
    favicon_url: str

    class Config:
        from_attributes = True


class ConfiguracionUpdate(BaseModel):
    logo_gym_url: str = ""
    logo_box_url: str = ""
    favicon_url: str = ""


# ── GET /configuracion — Obtener configuración ──────────

@router.get("", response_model=ConfiguracionOut, summary="Obtener configuración")
def get_configuracion(db: Session = Depends(get_db)):
    config = db.query(Configuracion).first()
    if not config:
        config = Configuracion(logo_gym_url="", logo_box_url="", favicon_url="")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# ── PUT /configuracion — Actualizar configuración ───────

@router.put("", response_model=ConfiguracionOut, summary="Actualizar configuración")
def update_configuracion(
    datos: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    config = db.query(Configuracion).first()
    if not config:
        config = Configuracion()
        db.add(config)

    config.logo_gym_url = datos.logo_gym_url
    config.logo_box_url = datos.logo_box_url
    config.favicon_url = datos.favicon_url
    db.commit()
    db.refresh(config)
    logger.info("Configuración actualizada por %s", admin.username)
    return config
