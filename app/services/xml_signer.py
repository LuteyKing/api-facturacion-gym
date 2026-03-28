"""
Simulador de firma electrónica XAdES-BES para desarrollo.

MODO SIMULACIÓN:
  Este módulo NO firma realmente el XML. En su lugar:
    1. Parsea el XML con lxml para validar que la estructura esté intacta.
    2. Emite un WARNING indicando que la firma es simulada.
    3. Retorna el XML original sin modificaciones.

  Esto permite que el flujo completo de la API funcione end-to-end
  sin necesidad de un certificado .p12 real del SRI.

  Cuando obtengas tu firma electrónica real, reemplaza este archivo
  con la implementación criptográfica completa (signxml + pyOpenSSL).
"""

import logging

from lxml import etree

logger = logging.getLogger(__name__)


def firmar_xml(xml_bytes: bytes) -> bytes:
    """Simula la firma XAdES-BES de un comprobante XML.

    En modo simulación:
      1. Parsea el XML para verificar que no esté corrupto.
      2. Registra un WARNING en los logs.
      3. Retorna el XML limpio (sin firma real).

    Args:
        xml_bytes: XML sin firmar generado por xml_generator.

    Returns:
        El mismo XML como bytes codificados en UTF-8 (sin firma).

    Raises:
        etree.XMLSyntaxError: Si el XML recibido tiene errores de sintaxis.
        ValueError: Si el XML está vacío o no se puede procesar.
    """
    # ── Validación 1: bytes no vacíos ────────────────────
    if not xml_bytes or not xml_bytes.strip():
        raise ValueError(
            "El XML recibido está vacío. Verifique que xml_generator "
            "haya producido el comprobante correctamente."
        )

    # ── Validación 2: parsear con lxml ───────────────────
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        logger.error("XML con errores de sintaxis: %s", e)
        raise

    # Verificar que el elemento raíz exista y tenga contenido
    tag_raiz = etree.QName(root).localname if root.tag else root.tag
    num_hijos = len(root)

    if num_hijos == 0:
        logger.warning(
            "El XML tiene un elemento raíz <%s> pero no contiene hijos.",
            tag_raiz,
        )

    # ── Simulación de firma ──────────────────────────────
    logger.warning(
        "⚠️ MODO SIMULACIÓN: El XML no está firmado realmente. "
        "Tag raíz: <%s>, hijos directos: %d. "
        "Para producción, reemplace este mock con la firma XAdES-BES real.",
        tag_raiz,
        num_hijos,
    )

    # ── Retornar XML limpio (re-serializado) ─────────────
    xml_limpio = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )

    logger.info(
        "XML procesado en modo simulación (%d bytes). "
        "Continuando flujo sin firma criptográfica.",
        len(xml_limpio),
    )

    return xml_limpio
