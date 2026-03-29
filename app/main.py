"""
API REST — Microservicio de Facturación Electrónica SRI Ecuador (offline)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .models import db_models  # noqa: F401  — registra los modelos en Base.metadata
from .models.db_models import Usuario
from .routers import auth, clientes, facturas, facturar, productos
from .routers.auth import hash_password

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# ── Crear tablas en la BD al iniciar ─────────────────────
Base.metadata.create_all(bind=engine)

# ── Seed: crear usuario admin por defecto ────────────────
def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.username == "admin").first():
            admin = Usuario(
                username="admin",
                password_hash=hash_password("admin123"),
                nombre_completo="Administrador",
                rol="admin",
            )
            db.add(admin)
            db.commit()
            logging.getLogger(__name__).info("Usuario admin creado por defecto")
    finally:
        db.close()

_seed_admin()

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

app.include_router(auth.router, prefix="/api/v1")
app.include_router(facturar.router, prefix="/api/v1")
app.include_router(facturas.router, prefix="/api/v1")
app.include_router(clientes.router, prefix="/api/v1")
app.include_router(productos.router, prefix="/api/v1")

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "servicio": "Facturación Electrónica SRI"}
