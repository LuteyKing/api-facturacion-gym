"""
API REST — Microservicio de Facturación Electrónica SRI Ecuador (offline)
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import Base, SessionLocal, engine
from .models import db_models  # noqa: F401  — registra los modelos en Base.metadata
from .models.db_models import Usuario, Configuracion
from .routers import auth, clientes, configuracion, dashboard, facturas, facturar, productos, usuarios
from .routers.auth import hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# ── Crear tablas en la BD al iniciar ─────────────────────
Base.metadata.create_all(bind=engine)

# ── Migración: agregar columna "sede" si no existe ───────
def _run_sede_migration():
    """Agrega la columna sede a facturas, clientes y productos si no existe."""
    tables = ["facturas", "clientes", "productos"]
    with engine.connect() as conn:
        for table in tables:
            conn.execute(text(
                f"ALTER TABLE {table} "
                f"ADD COLUMN IF NOT EXISTS sede VARCHAR(10) DEFAULT 'gym'"
            ))
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_sede ON {table} (sede)"
            ))
            conn.execute(text(
                f"UPDATE {table} SET sede = 'gym' WHERE sede IS NULL"
            ))
        conn.commit()
        logger.info("Migración sede completada correctamente")

def _run_configuracion_migration():
    """Convierte columnas de configuracion de VARCHAR a TEXT para Base64."""
    cols = ["logo_gym_url", "logo_box_url", "favicon_url"]
    with engine.connect() as conn:
        for col in cols:
            conn.execute(text(
                f"ALTER TABLE configuracion ALTER COLUMN {col} TYPE TEXT"
            ))
        conn.commit()
        logger.info("Migración configuracion (TEXT) completada")

try:
    _run_sede_migration()
except Exception as e:
    logger.warning("Migración sede omitida (posiblemente ya aplicada): %s", e)

try:
    _run_configuracion_migration()
except Exception as e:
    logger.warning("Migración configuracion omitida: %s", e)

app = FastAPI(
    title="Microservicio de Facturación Electrónica SRI — Ecuador",
    description=(
        "API REST para la emisión de comprobantes electrónicos (facturas) "
        "ante el Servicio de Rentas Internas del Ecuador, modalidad offline.\n\n"
        "**Endpoints principales:**\n"
        "- `POST /api/v1/facturar` — JSON simplificado (recomendado)\n"
        "- `POST /api/v1/facturas` — JSON con estructura SRI completa\n"
        "- `GET  /api/v1/facturas/autorizacion/{clave}` — consultar autorización"
    ),
    version="1.0.0",
)

# ── CORS — Permite peticiones desde cualquier origen ─────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(facturar.router, prefix="/api/v1")
app.include_router(facturas.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(productos.router, prefix="/api/v1")
app.include_router(usuarios.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(configuracion.router, prefix="/api/v1")

# ── Seed: crear usuario admin por defecto al arrancar ────
@app.on_event("startup")
def seed_admin():
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.username == "admin").first():
            password_plano = "admin123"
            print(f"DEBUG: Hasheando password de longitud: {len(password_plano)}")
            hash_generado = hash_password(password_plano)
            admin = Usuario(
                username="admin",
                password_hash=hash_generado,
                nombre_completo="Administrador",
                rol="admin",
                created_at=datetime.now(ZoneInfo("America/Guayaquil")).replace(tzinfo=None),
            )
            db.add(admin)
            db.commit()
            logging.getLogger(__name__).info("Usuario admin creado por defecto")

        # Seed: fila de configuración por defecto
        if not db.query(Configuracion).first():
            db.add(Configuracion(logo_gym_url="", logo_box_url="", favicon_url=""))
            db.commit()
            logging.getLogger(__name__).info("Configuración por defecto creada")
    finally:
        db.close()


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "servicio": "Facturación Electrónica SRI"}
