"""
Endpoint de estadísticas del Dashboard para administradores.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import Cliente, Factura, Producto, Usuario
from .auth import require_admin, get_current_user

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


class VentaDetalleCierre(BaseModel):
    secuencial: str
    cliente_nombre: str
    cliente_cedula: str
    total: float
    hora: str
    vendedor: str


class CierreCajaResponse(BaseModel):
    fecha: str
    total_recaudado: float
    cantidad_facturas: int
    detalle_ventas: list[VentaDetalleCierre]


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
    sede: str | None = Query(None, description="Filtrar por sede: gym o box"),
):
    ahora = datetime.now(EC_TZ).replace(tzinfo=None)
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    hace_30d = ahora - timedelta(days=30)

    # ── Ventas de hoy ────────────────────────────────────
    q_hoy = db.query(func.coalesce(func.sum(Factura.total), 0), func.count(Factura.id)).filter(Factura.created_at >= hoy_inicio)
    if sede:
        q_hoy = q_hoy.filter(Factura.sede == sede)
    resultado_hoy = q_hoy.first()
    ventas_hoy = float(resultado_hoy[0])
    facturas_hoy = int(resultado_hoy[1])

    # ── Clientes ─────────────────────────────────────────
    q_clientes = db.query(func.count(Cliente.id))
    if sede:
        q_clientes = q_clientes.filter(Cliente.sede == sede)
    clientes_total = q_clientes.scalar() or 0
    q_clientes_new = db.query(func.count(Cliente.id)).filter(Cliente.created_at >= hace_30d)
    if sede:
        q_clientes_new = q_clientes_new.filter(Cliente.sede == sede)
    clientes_nuevos_30d = q_clientes_new.scalar() or 0

    # ── Productos ────────────────────────────────────────
    q_prod = db.query(func.count(Producto.id))
    if sede:
        q_prod = q_prod.filter(Producto.sede == sede)
    productos_total = q_prod.scalar() or 0
    q_prod_recent = db.query(Producto).order_by(Producto.created_at.desc())
    if sede:
        q_prod_recent = q_prod_recent.filter(Producto.sede == sede)
    productos_recientes = q_prod_recent.limit(5).all()

    # ── Resumen semanal (últimos 7 días) ─────────────────
    resumen_semanal = []
    for i in range(6, -1, -1):
        dia = hoy_inicio - timedelta(days=i)
        dia_fin = dia + timedelta(days=1)
        q_dia = db.query(func.coalesce(func.sum(Factura.total), 0)).filter(Factura.created_at >= dia, Factura.created_at < dia_fin)
        if sede:
            q_dia = q_dia.filter(Factura.sede == sede)
        total_dia = q_dia.scalar()
        resumen_semanal.append(VentaDia(
            fecha=dia.strftime("%d/%m"),
            total=float(total_dia),
        ))

    # ── Ventas por producto (últimos 30 días) ────────────
    ventas_por_producto: dict[str, float] = defaultdict(float)
    q_f30 = db.query(Factura.xml_generado).filter(Factura.created_at >= hace_30d, Factura.xml_generado.isnot(None))
    if sede:
        q_f30 = q_f30.filter(Factura.sede == sede)
    facturas_30d = q_f30.all()
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


# ── GET /dashboard/cierre-caja ───────────────────────────
@router.get("/cierre-caja", response_model=CierreCajaResponse, summary="Cierre de Caja Diario")
def cierre_caja(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    sede: str | None = Query(None, description="Filtrar por sede: gym o box"),
):
    """Retorna el resumen de ventas del día actual para cuadre de caja."""
    ahora = datetime.now(EC_TZ).replace(tzinfo=None)
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    # Query base: facturas de hoy con JOIN a clientes y usuarios
    query = (
        db.query(Factura, Cliente.nombre_completo, Usuario.nombre_completo)
        .outerjoin(Cliente, Factura.identificacion_cliente == Cliente.cedula_ruc)
        .outerjoin(Usuario, Factura.usuario_id == Usuario.id)
        .filter(Factura.created_at >= hoy_inicio)
    )

    if sede:
        query = query.filter(Factura.sede == sede)

    # Vendedores solo ven sus propias ventas
    if current_user.rol != "admin":
        query = query.filter(Factura.usuario_id == current_user.id)

    filas = query.order_by(Factura.created_at.asc()).all()

    detalle = []
    total_recaudado = 0.0
    for factura, nombre_cliente, nombre_vendedor in filas:
        monto = float(factura.total)
        total_recaudado += monto
        detalle.append(VentaDetalleCierre(
            secuencial=factura.secuencial,
            cliente_nombre=nombre_cliente or "Consumidor Final",
            cliente_cedula=factura.identificacion_cliente,
            total=monto,
            hora=factura.created_at.strftime("%H:%M") if factura.created_at else "—",
            vendedor=nombre_vendedor or "—",
        ))

    return CierreCajaResponse(
        fecha=ahora.strftime("%d/%m/%Y"),
        total_recaudado=round(total_recaudado, 2),
        cantidad_facturas=len(detalle),
        detalle_ventas=detalle,
    )
