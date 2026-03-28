"""
Configuración de la base de datos SQLite con SQLAlchemy.

Crea y gestiona la conexión a `facturacion_sri_core.db`, almacenada
en la raíz del proyecto.  El archivo se genera automáticamente
la primera vez que se levanta la API.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Ruta de la base de datos ─────────────────────────────
# Se ubica junto a main.py / requirements.txt para fácil acceso.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "facturacion_sri_core.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── Engine y Session ─────────────────────────────────────
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # requerido por SQLite + FastAPI
    echo=False,  # cambiar a True para depurar SQL en consola
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base declarativa (estilo SQLAlchemy 2.0) ─────────────
class Base(DeclarativeBase):
    pass


# ── Dependency de FastAPI ────────────────────────────────
def get_db():
    """Genera una sesión de BD por request y la cierra al finalizar.

    Uso en endpoints:
        @router.post("/ejemplo")
        def mi_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
