import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Ruta de la base de datos ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Obtenemos la URL de Render (Supabase). Si no existe, usamos SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Configuración para la nube: PostgreSQL (Supabase en Render)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
else:
    # Configuración para local: SQLite (Tu computadora)
    DB_PATH = BASE_DIR / "facturacion_sri_core.db"
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # requerido solo por SQLite
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base declarativa (estilo SQLAlchemy 2.0) ─────────────
class Base(DeclarativeBase):
    pass

# ── Dependency de FastAPI ────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()