from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.db_models import Producto
from pydantic import BaseModel

router = APIRouter(prefix="/productos", tags=["Productos"])

class ProductoCreate(BaseModel):
    codigo: str
    nombre: str
    precio_unitario: float
    iva_aplica: bool = True

class ProductoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    precio_unitario: float
    iva_aplica: bool
    created_at: str | None = None

    class Config:
        from_attributes = True


def _formato_fecha_ec(dt):
    """Convierte un datetime UTC a string DD/MM/YYYY HH:MM:SS en hora Ecuador (UTC-5)."""
    if not dt:
        return None
    return (dt - timedelta(hours=5)).strftime("%d/%m/%Y %H:%M:%S")


@router.post("", response_model=ProductoResponse)
def crear_producto(producto: ProductoCreate, db: Session = Depends(get_db)):
    db_prod = Producto(**producto.dict())
    try:
        db.add(db_prod)
        db.commit()
        db.refresh(db_prod)
        return ProductoResponse(
            id=db_prod.id,
            codigo=db_prod.codigo,
            nombre=db_prod.nombre,
            precio_unitario=db_prod.precio_unitario,
            iva_aplica=db_prod.iva_aplica,
            created_at=_formato_fecha_ec(db_prod.created_at),
        )
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="El código de producto ya existe")

@router.get("", response_model=list[ProductoResponse])
def listar_productos(db: Session = Depends(get_db)):
    productos = db.query(Producto).all()
    return [
        ProductoResponse(
            id=p.id,
            codigo=p.codigo,
            nombre=p.nombre,
            precio_unitario=p.precio_unitario,
            iva_aplica=p.iva_aplica,
            created_at=_formato_fecha_ec(p.created_at),
        )
        for p in productos
    ]