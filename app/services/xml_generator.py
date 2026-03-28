"""
Generador de XML de factura electrónica conforme al esquema XSD del SRI.

Produce el XML sin firmar, listo para ser procesado por el módulo de firma.
Versión de factura: 1.1.0
Nodos obligatorios que se generan por diseño:
  - <infoTributaria>: ambiente, tipoEmision, razonSocial, ruc, claveAcceso,
                       codDoc(01), estab, ptoEmi, secuencial, dirMatriz.
  - <infoFactura>: fechaEmision, obligadoContabilidad,
                    tipoIdentificacionComprador, razonSocialComprador,
                    identificacionComprador, totalSinImpuestos,
                    totalDescuento, totalConImpuestos (agrupado por código),
                    propina, importeTotal, moneda, pagos.
  - <detalles>: cada <detalle> incluye obligatoriamente <impuestos>
                con al menos un <impuesto> (IVA código 2, incluso tarifa 0%).
  - <infoAdicional>: campos opcionales (email, teléfono, dirección, etc.)."""

from decimal import Decimal
from lxml import etree

from ..config import settings
from ..models.schemas import FacturaRequest


def _fmt(valor: Decimal, decimales: int = 2) -> str:
    """Formatea un Decimal a string con la cantidad fija de decimales."""
    return f"{valor:.{decimales}f}"


def generar_xml_factura(factura: FacturaRequest, clave_acceso: str) -> bytes:
    """Construye el XML de la factura según la estructura del SRI.

    Args:
        factura: Datos de la factura validados por Pydantic.
        clave_acceso: Clave de acceso de 49 dígitos ya generada.

    Returns:
        XML como bytes codificado en UTF-8.
    """
    root = etree.Element("factura", id="comprobante", version="1.1.0")

    # ── infoTributaria ───────────────────────────────────
    info_trib = etree.SubElement(root, "infoTributaria")
    _tag(info_trib, "ambiente", str(settings.SRI_AMBIENTE))
    _tag(info_trib, "tipoEmision", str(settings.SRI_TIPO_EMISION))
    _tag(info_trib, "razonSocial", settings.EMISOR_RAZON_SOCIAL)
    if settings.EMISOR_NOMBRE_COMERCIAL:
        _tag(info_trib, "nombreComercial", settings.EMISOR_NOMBRE_COMERCIAL)
    _tag(info_trib, "ruc", settings.EMISOR_RUC)
    _tag(info_trib, "claveAcceso", clave_acceso)
    _tag(info_trib, "codDoc", "01")  # Factura
    _tag(info_trib, "estab", settings.EMISOR_ESTABLECIMIENTO)
    _tag(info_trib, "ptoEmi", settings.EMISOR_PUNTO_EMISION)
    _tag(info_trib, "secuencial", factura.secuencial)
    _tag(info_trib, "dirMatriz", settings.EMISOR_DIR_MATRIZ)

    # ── infoFactura ──────────────────────────────────────
    info_fact = etree.SubElement(root, "infoFactura")
    inf = factura.info_factura

    _tag(info_fact, "fechaEmision", inf.fecha_emision)

    if inf.dir_establecimiento or settings.EMISOR_DIR_ESTABLECIMIENTO:
        _tag(
            info_fact,
            "dirEstablecimiento",
            inf.dir_establecimiento or settings.EMISOR_DIR_ESTABLECIMIENTO,
        )

    if settings.EMISOR_CONTRIBUYENTE_ESPECIAL or inf.contribuyente_especial:
        _tag(
            info_fact,
            "contribuyenteEspecial",
            inf.contribuyente_especial or settings.EMISOR_CONTRIBUYENTE_ESPECIAL,
        )

    # obligadoContabilidad — OBLIGATORIO según Ficha Técnica SRI
    _tag(info_fact, "obligadoContabilidad", inf.obligado_contabilidad)

    # tipoIdentificacionComprador — OBLIGATORIO: '04'=RUC, '05'=Cédula, etc.
    _tag(
        info_fact,
        "tipoIdentificacionComprador",
        inf.tipo_identificacion_comprador.value,
    )
    _tag(info_fact, "razonSocialComprador", inf.razon_social_comprador)
    _tag(info_fact, "identificacionComprador", inf.identificacion_comprador)

    if inf.direccion_comprador:
        _tag(info_fact, "direccionComprador", inf.direccion_comprador)

    _tag(info_fact, "totalSinImpuestos", _fmt(inf.total_sin_impuestos))
    _tag(info_fact, "totalDescuento", _fmt(inf.total_descuento))

    # totalConImpuestos — OBLIGATORIO según Ficha Técnica SRI
    # Agrupa las bases imponibles por código de impuesto y código de porcentaje.
    total_con_imp = etree.SubElement(info_fact, "totalConImpuestos")
    for ti in inf.total_con_impuestos:
        node = etree.SubElement(total_con_imp, "totalImpuesto")
        _tag(node, "codigo", ti.codigo.value)
        _tag(node, "codigoPorcentaje", ti.codigo_porcentaje.value)
        if ti.descuento_adicional > 0:
            _tag(node, "descuentoAdicional", _fmt(ti.descuento_adicional))
        _tag(node, "baseImponible", _fmt(ti.base_imponible))
        _tag(node, "valor", _fmt(ti.valor))

    _tag(info_fact, "propina", _fmt(inf.propina))
    _tag(info_fact, "importeTotal", _fmt(inf.importe_total))
    _tag(info_fact, "moneda", inf.moneda)

    # pagos
    pagos_node = etree.SubElement(info_fact, "pagos")
    for pago in inf.pagos:
        pago_node = etree.SubElement(pagos_node, "pago")
        _tag(pago_node, "formaPago", pago.forma_pago.value)
        _tag(pago_node, "total", _fmt(pago.total))
        if pago.plazo is not None:
            _tag(pago_node, "plazo", str(pago.plazo))
            _tag(pago_node, "unidadTiempo", pago.unidad_tiempo or "dias")

    # ── detalles ─────────────────────────────────────────
    # Cada <detalle> DEBE contener <impuestos> con al menos un <impuesto>.
    # Incluso si el servicio grava IVA 0%: código=2, codigoPorcentaje=0, tarifa=0.
    detalles_node = etree.SubElement(root, "detalles")
    for det in factura.detalles:
        det_node = etree.SubElement(detalles_node, "detalle")
        _tag(det_node, "codigoPrincipal", det.codigo_principal)
        if det.codigo_auxiliar:
            _tag(det_node, "codigoAuxiliar", det.codigo_auxiliar)
        _tag(det_node, "descripcion", det.descripcion)
        _tag(det_node, "cantidad", _fmt(det.cantidad, 6))
        _tag(det_node, "precioUnitario", _fmt(det.precio_unitario, 6))
        _tag(det_node, "descuento", _fmt(det.descuento))
        _tag(det_node, "precioTotalSinImpuesto", _fmt(det.precio_total_sin_impuesto))

        # <impuestos> — OBLIGATORIO por cada detalle (Ficha Técnica SRI).
        # El SRI RECHAZA comprobantes cuyo detalle no incluya este nodo.
        impuestos_node = etree.SubElement(det_node, "impuestos")
        for imp in det.impuestos:
            imp_node = etree.SubElement(impuestos_node, "impuesto")
            _tag(imp_node, "codigo", imp.codigo.value)             # 2=IVA
            _tag(imp_node, "codigoPorcentaje", imp.codigo_porcentaje.value)  # 0,2,3,4,5,6,7
            _tag(imp_node, "tarifa", _fmt(imp.tarifa))
            _tag(imp_node, "baseImponible", _fmt(imp.base_imponible))
            _tag(imp_node, "valor", _fmt(imp.valor))

    # ── infoAdicional (opcional) ─────────────────────────
    # Campos libres: email, teléfono, dirección, observaciones, etc.
    if factura.info_adicional:
        info_adic = etree.SubElement(root, "infoAdicional")
        for nombre, valor in factura.info_adicional.items():
            campo = etree.SubElement(info_adic, "campoAdicional")
            campo.set("nombre", nombre[:300])
            campo.text = str(valor)[:300]

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )
    return xml_bytes


def _tag(parent: etree._Element, nombre: str, texto: str) -> etree._Element:
    """Agrega un sub-elemento con texto al nodo padre."""
    elem = etree.SubElement(parent, nombre)
    elem.text = texto
    return elem
