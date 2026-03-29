"""
Configuración centralizada del microservicio de facturación electrónica SRI.

TODAS las configuraciones del emisor se leen desde variables de entorno.
Copie el archivo .env.example a .env y complete sus datos reales.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Intentar cargar el .env si existe
load_dotenv()

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carpeta local donde se almacenan los certificados .p12
CERTIFICADOS_DIR = BASE_DIR / "certificados"


class Settings:
    """Configuración del microservicio — lee TODO desde variables de entorno."""

    # ── Entorno SRI ──────────────────────────────────────
    # 1 para Pruebas, 2 para Producción
    SRI_AMBIENTE: int = int(os.getenv("SRI_AMBIENTE", "1"))
    SRI_TIPO_EMISION: int = int(os.getenv("SRI_TIPO_EMISION", "1"))

    # URLs de los web services del SRI (offline)
    _URLS = {
        1: {
            "recepcion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
            "autorizacion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
        },
        2: {
            "recepcion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
            "autorizacion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
        },
    }

    @property
    def url_recepcion(self) -> str:
        return self._URLS[self.SRI_AMBIENTE]["recepcion"]

    @property
    def url_autorizacion(self) -> str:
        return self._URLS[self.SRI_AMBIENTE]["autorizacion"]

    # ── Datos del emisor (desde .env) ────────────────────
    EMISOR_RUC: str = os.getenv("EMISOR_RUC", "0000000000001")
    EMISOR_RAZON_SOCIAL: str = os.getenv("EMISOR_RAZON_SOCIAL", "MI EMPRESA S.A.")
    EMISOR_NOMBRE_COMERCIAL: str = os.getenv("EMISOR_NOMBRE_COMERCIAL", "MI EMPRESA")
    EMISOR_DIR_MATRIZ: str = os.getenv("EMISOR_DIR_MATRIZ", "Dirección Matriz")
    EMISOR_DIR_ESTABLECIMIENTO: str = os.getenv("EMISOR_DIR_ESTABLECIMIENTO", "Dirección Establecimiento")
    EMISOR_OBLIGADO_CONTABILIDAD: str = os.getenv("EMISOR_OBLIGADO_CONTABILIDAD", "NO")
    EMISOR_CONTRIBUYENTE_ESPECIAL: str = os.getenv("EMISOR_CONTRIBUYENTE_ESPECIAL", "")
    EMISOR_ESTABLECIMIENTO: str = os.getenv("EMISOR_ESTABLECIMIENTO", "001")
    EMISOR_PUNTO_EMISION: str = os.getenv("EMISOR_PUNTO_EMISION", "001")

    # ── Firma electrónica ────────────────────────────────
    _FIRMA_ARCHIVO: str = os.getenv("FIRMA_ELECTRONICA_ARCHIVO", "firma.p12")
    FIRMA_ELECTRONICA_PASSWORD: str = os.getenv("FIRMA_ELECTRONICA_PASSWORD", "")

    @property
    def FIRMA_ELECTRONICA_PATH(self) -> Path:
        """Ruta absoluta al archivo .p12 dentro de certificados/."""
        return CERTIFICADOS_DIR / self._FIRMA_ARCHIVO

    # ── JWT / Autenticación ──────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "cambiar-esta-clave-en-produccion")
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "480"))


settings = Settings()