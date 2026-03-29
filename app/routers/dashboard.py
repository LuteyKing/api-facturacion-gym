"""
Endpoint de estadísticas del Dashboard para administradores.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Cliente, Factura, Producto, Usuario
from .auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

EC_TZ = ZoneInfo("America/Guayaquil")


# ── Schemas de respuesta ─────────────────────────────────
class VentaDia(BaseModel):
    fecha: str
    total: float


class ProductoStock(BaseModel):
    nombre: str
    codigo: str
    precio: float


class CategoriaVenta(BaseModel):
    nombre: str
    total: float


class DashboardStats(BaseModel):
    ventas_hoy: float
    facturas_hoy: int
    clientes_total: int
    clientes_nuevos_30d: int
    productos_total: int
    productos_recientes: list[ProductoStock]
    resumen_semanal: list[VentaDia]
    ventas_por_producto: list[CategoriaVenta]


# ── GET /dashboard/stats ─────────────────────────────────
@router.get("/stats", response_model=DashboardStats, summary="Estadísticas del Dashboard (Admin)")
def obtener_stats(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    ahora = datetime.now(EC_TZ).replace(tzinfo=None)
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    hace_30d = ahora - timedelta(days=30)

    # ── Ventas de hoy ────────────────────────────────────
    resultado_hoy = (
        db.query(func.coalesce(func.sum(Factura.total), 0), func.count(Factura.id))
        .filter(Factura.created_at >= hoy_inicio)
        .first()
    )
    ventas_hoy = float(resultado_hoy[0])
    facturas_hoy = int(resultado_hoy[1])

    # ── Clientes ─────────────────────────────────────────
    clientes_total = db.query(func.count(Cliente.id)).scalar() or 0
    clientes_nuevos_30d = (
        db.query(func.count(Cliente.id))
        .filter(Cliente.created_at >= hace_30d)
        .scalar() or 0
    )

    # ── Productos ────────────────────────────────────────
    productos_total = db.query(func.count(Producto.id)).scalar() or 0
    productos_recientes = (
        db.query(Producto)
        .order_by(Producto.created_at.desc())
        .limit(5)
        .all()
    )

    # ── Resumen semanal (últimos 7 días) ─────────────────
    resumen_semanal = []
    for i in range(6, -1, -1):
        dia = hoy_inicio - timedelta(days=i)
        dia_fin = dia + timedelta(days=1)
        total_dia = (
            db.query(func.coalesce(func.sum(Factura.total), 0))
            .filter(Factura.created_at >= dia, Factura.created_at < dia_fin)
            .scalar()
        )
        resumen_semanal.append(VentaDia(
            fecha=dia.strftime("%d/%m"),
            total=float(total_dia),
        ))

    # ── Ventas por producto (últimos 30 días) ────────────
    ventas_por_producto: dict[str, float] = defaultdict(float)
    facturas_30d = (
        db.query(Factura.xml_generado)
        .filter(Factura.created_at >= hace_30d, Factura.xml_generado.isnot(None))
        .all()
    )
    for (xml_str,) in facturas_30d:
        try:
            root = ET.fromstring(xml_str)
            for det in root.iter("detalle"):
                desc = det.findtext("descripcion", "Otro")
                subtotal = float(det.findtext("precioTotalSinImpuesto", "0"))
                ventas_por_producto[desc] += subtotal
        except Exception:
            pass

    top_productos = sorted(ventas_por_producto.items(), key=lambda x: x[1], reverse=True)[:8]

    return DashboardStats(
        ventas_hoy=ventas_hoy,
        facturas_hoy=facturas_hoy,
        clientes_total=clientes_total,
        clientes_nuevos_30d=clientes_nuevos_30d,
        productos_total=productos_total,
        productos_recientes=[
            ProductoStock(nombre=p.nombre, codigo=p.codigo, precio=float(p.precio_unitario))
            for p in productos_recientes
        ],
        resumen_semanal=resumen_semanal,
        ventas_por_producto=[
            CategoriaVenta(nombre=nombre, total=total)
            for nombre, total in top_productos
        ],
    )
