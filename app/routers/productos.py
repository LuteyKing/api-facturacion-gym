from datetime import timedelta, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models.db_models import Producto, Usuario
from .auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/productos", tags=["Productos"])

class ProductoCreate(BaseModel):
    codigo: str
    nombre: str
    precio_unitario: float
    iva_aplica: bool = True
    sede: str = "gym"

class ProductoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    precio_unitario: float
    iva_aplica: bool
    sede: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


def _formato_fecha_ec(dt):
    """Convierte un datetime UTC a string DD/MM/YYYY HH:MM:SS en hora Ecuador (UTC-5)."""
    if not dt:
        return None
    return (dt - timedelta(hours=5)).strftime("%d/%m/%Y %H:%M:%S")


@router.post("", response_model=ProductoResponse)
def crear_producto(producto: ProductoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    db_prod = Producto(
        codigo=producto.codigo,
        nombre=producto.nombre,
        precio_unitario=producto.precio_unitario,
        iva_aplica=producto.iva_aplica,
        sede=producto.sede,
        created_at=datetime.now(ZoneInfo("America/Guayaquil")).replace(tzinfo=None),
    )
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
            sede=db_prod.sede,
            created_at=_formato_fecha_ec(db_prod.created_at),
        )
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="El código de producto ya existe")

@router.get("", response_model=list[ProductoResponse])
def listar_productos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    sede: Optional[str] = Query(None, description="Filtrar por sede: gym o box"),
):
    query = db.query(Producto)
    if sede:
        query = query.filter(Producto.sede == sede)
    productos = query.all()
    return [
        ProductoResponse(
            id=p.id,
            codigo=p.codigo,
            nombre=p.nombre,
            precio_unitario=p.precio_unitario,
            iva_aplica=p.iva_aplica,
            sede=p.sede,
            created_at=_formato_fecha_ec(p.created_at),
        )
        for p in productos
    ]


# ── PUT /productos/{id} — Actualizar producto ────────────
class ProductoUpdate(BaseModel):
    nombre: str
    precio_unitario: float
    iva_aplica: bool = True


@router.put("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.nombre = datos.nombre
    producto.precio_unitario = datos.precio_unitario
    producto.iva_aplica = datos.iva_aplica
    db.commit()
    db.refresh(producto)
    return ProductoResponse(
        id=producto.id,
        codigo=producto.codigo,
        nombre=producto.nombre,
        precio_unitario=producto.precio_unitario,
        iva_aplica=producto.iva_aplica,
        sede=producto.sede,
        created_at=_formato_fecha_ec(producto.created_at),
    )


# ── DELETE /productos/{id} — Eliminar producto ───────────
@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(producto)
    db.commit()
    return {"detail": "Producto eliminado correctamente"}