"""
Generación de la clave de acceso de 49 dígitos según especificación del SRI.

Estructura (de izquierda a derecha):
  Pos  1- 8 : Fecha de emisión (ddmmyyyy)                        8 dígitos
  Pos  9-10 : Tipo de comprobante                                2 dígitos
  Pos 11-23 : RUC del emisor                                    13 dígitos
  Pos 24    : Tipo de ambiente (1=Pruebas, 2=Producción)          1 dígito
  Pos 25-27 : Establecimiento                                    3 dígitos
  Pos 28-30 : Punto de emisión                                   3 dígitos
  Pos 31-39 : Secuencial                                         9 dígitos
  Pos 40-47 : Código numérico (aleatorio)                        8 dígitos
  Pos 48    : Tipo de emisión (1=Normal)                          1 dígito
  Pos 49    : Dígito verificador (módulo 11)                      1 dígito
"""

import random


def _validar_solo_digitos(valor: str, campo: str, longitud: int) -> None:
    """Verifica que un campo sea numérico y tenga la longitud exacta."""
    if not valor.isdigit():
        raise ValueError(f"{campo} debe contener solo dígitos: '{valor}'")
    if len(valor) != longitud:
        raise ValueError(
            f"{campo} debe tener {longitud} dígitos, tiene {len(valor)}: '{valor}'"
        )


def _calcular_digito_verificador(clave_48: str) -> int:
    """Calcula el dígito verificador con el algoritmo Módulo 11 del SRI.

    Procedimiento (Ficha Técnica SRI):
      1. Se recorre la clave de 48 dígitos de DERECHA a IZQUIERDA.
      2. Se multiplica cada dígito por un peso cíclico: 2, 3, 4, 5, 6, 7.
      3. Se suman todos los productos.
      4. Se obtiene el residuo de dividir la suma para 11.
      5. El dígito verificador = 11 – residuo.
         - Si el resultado es 11 → dígito = 0
         - Si el resultado es 10 → dígito = 1
    """
    if len(clave_48) != 48 or not clave_48.isdigit():
        raise ValueError(
            f"Se esperan exactamente 48 dígitos numéricos, recibido: '{clave_48}'"
        )

    pesos = [2, 3, 4, 5, 6, 7]
    total = 0
    for i, digito in enumerate(reversed(clave_48)):
        total += int(digito) * pesos[i % len(pesos)]

    residuo = total % 11
    resultado = 11 - residuo

    if resultado == 11:
        return 0
    if resultado == 10:
        return 1
    return resultado


def generar_clave_acceso(
    fecha_emision: str,
    tipo_comprobante: str,
    ruc: str,
    ambiente: int,
    establecimiento: str,
    punto_emision: str,
    secuencial: str,
    tipo_emision: int = 1,
) -> str:
    """Genera la clave de acceso de 49 dígitos.

    Args:
        fecha_emision: Fecha en formato dd/mm/yyyy.
        tipo_comprobante: Código de tipo de documento (ej. '01' para factura).
        ruc: RUC del emisor (13 dígitos).
        ambiente: 1=Pruebas, 2=Producción.
        establecimiento: Código de establecimiento (3 dígitos).
        punto_emision: Código de punto de emisión (3 dígitos).
        secuencial: Número secuencial (9 dígitos).
        tipo_emision: 1=Normal.

    Returns:
        Clave de acceso de 49 dígitos.
    """
    # ── Validar cada campo individualmente ────────────
    partes = fecha_emision.split("/")
    if len(partes) != 3:
        raise ValueError(
            f"Formato de fecha inválido, se espera dd/mm/yyyy: '{fecha_emision}'"
        )
    fecha_fmt = f"{partes[0]}{partes[1]}{partes[2]}"  # ddmmyyyy
    _validar_solo_digitos(fecha_fmt, "fecha_emision", 8)
    _validar_solo_digitos(tipo_comprobante, "tipo_comprobante", 2)
    _validar_solo_digitos(ruc, "ruc", 13)
    _validar_solo_digitos(str(ambiente), "ambiente", 1)
    _validar_solo_digitos(establecimiento, "establecimiento", 3)
    _validar_solo_digitos(punto_emision, "punto_emision", 3)
    _validar_solo_digitos(secuencial, "secuencial", 9)
    _validar_solo_digitos(str(tipo_emision), "tipo_emision", 1)

    codigo_numerico = f"{random.randint(0, 99999999):08d}"

    # ── Concatenar los 48 dígitos ─────────────────────
    clave_48 = (
        f"{fecha_fmt}"           #  8 dígitos (pos  1- 8)
        f"{tipo_comprobante}"     #  2 dígitos (pos  9-10)
        f"{ruc}"                  # 13 dígitos (pos 11-23)
        f"{ambiente}"             #  1 dígito  (pos 24)
        f"{establecimiento}"      #  3 dígitos (pos 25-27)
        f"{punto_emision}"        #  3 dígitos (pos 28-30)
        f"{secuencial}"           #  9 dígitos (pos 31-39)
        f"{codigo_numerico}"      #  8 dígitos (pos 40-47)
        f"{tipo_emision}"         #  1 dígito  (pos 48)
    )                             # Total = 48 dígitos

    # ── Dígito verificador (Módulo 11) ────────────────
    digito = _calcular_digito_verificador(clave_48)
    clave_49 = f"{clave_48}{digito}"

    assert len(clave_49) == 49, f"Clave debe tener 49 dígitos: {len(clave_49)}"
    return clave_49
