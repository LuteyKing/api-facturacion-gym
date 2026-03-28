"""Enumeraciones oficiales del SRI para facturación electrónica."""

from enum import Enum


class Ambiente(str, Enum):
    PRUEBAS = "1"
    PRODUCCION = "2"


class TipoEmision(str, Enum):
    NORMAL = "1"


class TipoDocumento(str, Enum):
    FACTURA = "01"
    NOTA_CREDITO = "04"
    NOTA_DEBITO = "05"
    GUIA_REMISION = "06"
    RETENCION = "07"


class TipoIdentificacion(str, Enum):
    RUC = "04"
    CEDULA = "05"
    PASAPORTE = "06"
    CONSUMIDOR_FINAL = "07"
    EXTERIOR = "08"


class CodigoImpuesto(str, Enum):
    IVA = "2"
    ICE = "3"
    IRBPNR = "5"


class CodigoPorcentajeIVA(str, Enum):
    """Tabla 18 - Código de porcentaje de IVA (Ficha Técnica SRI)."""

    IVA_0 = "0"    # 0 %
    IVA_12 = "2"   # 12 %
    IVA_14 = "3"   # 14 %
    IVA_15 = "4"   # 15 %
    IVA_5 = "5"    # 5 %
    NO_OBJETO = "6" # No objeto de impuesto
    EXENTO = "7"   # Exento de IVA


# Tarifas reales asociadas a cada código de porcentaje
TARIFA_IVA: dict[CodigoPorcentajeIVA, int] = {
    CodigoPorcentajeIVA.IVA_0: 0,
    CodigoPorcentajeIVA.IVA_12: 12,
    CodigoPorcentajeIVA.IVA_14: 14,
    CodigoPorcentajeIVA.IVA_15: 15,
    CodigoPorcentajeIVA.IVA_5: 5,
    CodigoPorcentajeIVA.NO_OBJETO: 0,
    CodigoPorcentajeIVA.EXENTO: 0,
}


class FormaPago(str, Enum):
    SIN_SISTEMA_FINANCIERO = "01"
    COMPENSACION_DEUDAS = "15"
    TARJETA_DEBITO = "16"
    DINERO_ELECTRONICO = "17"
    TARJETA_PREPAGO = "18"
    TARJETA_CREDITO = "19"
    OTROS_SISTEMA_FINANCIERO = "20"
    ENDOSO_TITULOS = "21"