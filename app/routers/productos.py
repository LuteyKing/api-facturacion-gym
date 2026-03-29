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

@router.post("")
def crear_producto(producto: ProductoCreate, db: Session = Depends(get_db)):
    db_prod = Producto(**producto.dict())
    try:
        db.add(db_prod)
        db.commit()
        db.refresh(db_prod)
        return db_prod
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="El código de producto ya existe")

@router.get("")
def listar_productos(db: Session = Depends(get_db)):
    return db.query(Producto).all()