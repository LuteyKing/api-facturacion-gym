"""
Generador de RIDE (Representación Impresa del Documento Electrónico).

Produce un PDF premium con diseño corporativo de Gimnasio/CrossFit,
usando paleta Negro + Amarillo Atlético (#FFD700).

Dependencias: reportlab, qrcode, pillow.
"""

import io
import logging
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..config import settings

logger = logging.getLogger(__name__)

# ── Paleta de colores corporativa — Gimnasio/CrossFit ────
COLOR_NEGRO = colors.HexColor("#111111")           # Negro principal
COLOR_NEGRO_HEADER = colors.HexColor("#0D0D0D")    # Negro profundo para encabezado
COLOR_AMARILLO = colors.HexColor("#FFD700")         # Amarillo Atlético (acento)
COLOR_AMARILLO_SUAVE = colors.HexColor("#FFF3CD")   # Amarillo claro para fondos
COLOR_FONDO_GRIS = colors.HexColor("#F7F7F7")       # Gris ultra claro para datos
COLOR_BORDE_GRIS = colors.HexColor("#D0D0D0")       # Gris para bordes finos
COLOR_TEXTO_OSCURO = colors.HexColor("#1A1A1A")     # Texto principal oscuro
COLOR_TEXTO_GRIS = colors.HexColor("#555555")        # Texto secundario
COLOR_BLANCO = colors.white
COLOR_FILA_ALT = colors.HexColor("#FAFAFA")          # Filas alternas


def _generar_qr(clave_acceso: str) -> io.BytesIO:
    """Genera un código QR con la clave de acceso (49 dígitos)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(clave_acceso)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111111", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generar_ride_pdf(factura) -> bytes:
    """Genera el PDF del RIDE a partir de un registro de Factura (SQLAlchemy).

    Args:
        factura: Instancia del modelo db_models.Factura con los campos:
                 id, secuencial, fecha_emision, identificacion_cliente,
                 total, clave_acceso, estado_sri, created_at.

    Returns:
        Contenido del PDF como bytes.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
    )

    PAGE_WIDTH = A4[0] - 3.6 * cm  # Ancho útil de la página
    COL_TOTAL = PAGE_WIDTH          # Ancho total disponible

    # ── Estilos ──────────────────────────────────────────
    styles = getSampleStyleSheet()

    estilo_header_empresa = ParagraphStyle(
        "HeaderEmpresa",
        fontSize=16,
        textColor=COLOR_BLANCO,
        fontName="Helvetica-Bold",
        leading=20,
    )

    estilo_header_detalle = ParagraphStyle(
        "HeaderDetalle",
        fontSize=9,
        textColor=COLOR_AMARILLO,
        fontName="Helvetica",
        leading=12,
    )

    estilo_header_ride = ParagraphStyle(
        "HeaderRide",
        fontSize=22,
        textColor=COLOR_AMARILLO,
        fontName="Helvetica-Bold",
        alignment=2,  # right
        leading=26,
    )

    estilo_header_ride_sub = ParagraphStyle(
        "HeaderRideSub",
        fontSize=9,
        textColor=colors.HexColor("#BBBBBB"),
        fontName="Helvetica",
        alignment=2,
        leading=12,
    )

    estilo_seccion = ParagraphStyle(
        "SeccionTitulo",
        fontSize=11,
        textColor=COLOR_NEGRO,
        fontName="Helvetica-Bold",
        spaceBefore=2 * mm,
        spaceAfter=3 * mm,
    )

    estilo_campo_label = ParagraphStyle(
        "CampoLabel",
        fontSize=8,
        textColor=COLOR_TEXTO_GRIS,
        fontName="Helvetica",
        leading=10,
    )

    estilo_campo_valor = ParagraphStyle(
        "CampoValor",
        fontSize=10,
        textColor=COLOR_TEXTO_OSCURO,
        fontName="Helvetica-Bold",
        leading=13,
    )

    estilo_normal = ParagraphStyle(
        "NormalRIDE",
        parent=styles["Normal"],
        fontSize=9,
        textColor=COLOR_TEXTO_OSCURO,
        fontName="Helvetica",
        leading=13,
    )

    estilo_disclaimer = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#999999"),
        fontName="Helvetica-Oblique",
        alignment=1,  # center
    )

    estilo_clave = ParagraphStyle(
        "ClaveAcceso",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_NEGRO,
        fontName="Courier-Bold",
        alignment=1,
        spaceAfter=4 * mm,
        leading=14,
    )

    # ── Elementos del PDF ────────────────────────────────
    elementos = []

    # ═══════════════════════════════════════════════════════
    # ─── FRANJA SUPERIOR NEGRA (Header Principal) ─────────
    # ═══════════════════════════════════════════════════════
    # Columna izquierda: Nombre del Gimnasio + RUC
    # Columna derecha: "RIDE" + tipo documento
    header_left_content = (
        f'<font name="Helvetica-Bold" size="16" color="#FFFFFF">'
        f'{settings.EMISOR_RAZON_SOCIAL}</font><br/>'
        f'<font name="Helvetica" size="9" color="#FFD700">'
        f'{settings.EMISOR_NOMBRE_COMERCIAL} &nbsp;|&nbsp; RUC: {settings.EMISOR_RUC}</font><br/>'
        f'<font name="Helvetica" size="8" color="#AAAAAA">'
        f'{settings.EMISOR_DIR_ESTABLECIMIENTO}</font>'
    )

    header_right_content = (
        f'<font name="Helvetica-Bold" size="22" color="#FFD700">RIDE</font><br/>'
        f'<font name="Helvetica" size="9" color="#BBBBBB">Comprobante Electrónico</font>'
    )

    header_data = [
        [
            Paragraph(header_left_content, ParagraphStyle("HL", leading=16)),
            Paragraph(header_right_content, ParagraphStyle("HR", alignment=2, leading=16)),
        ]
    ]
    header_table = Table(header_data, colWidths=[COL_TOTAL * 0.65, COL_TOTAL * 0.35])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_NEGRO_HEADER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (0, 0), 16),
                ("RIGHTPADDING", (-1, -1), (-1, -1), 16),
                ("ROUNDEDCORNERS", [6, 6, 0, 0]),
            ]
        )
    )
    elementos.append(header_table)

    # ─── Franja amarilla de acento ────────────────────────
    barra_amarilla = Table([[""]], colWidths=[COL_TOTAL], rowHeights=[4 * mm])
    barra_amarilla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_AMARILLO),
                ("ROUNDEDCORNERS", [0, 0, 6, 6]),
            ]
        )
    )
    elementos.append(barra_amarilla)
    elementos.append(Spacer(1, 8 * mm))

    # ═══════════════════════════════════════════════════════
    # ─── DATOS DEL CLIENTE / FACTURA ──────────────────────
    # ═══════════════════════════════════════════════════════
    # Título de sección con ícono visual
    seccion_titulo = Table(
        [[
            Paragraph(
                '<font name="Helvetica-Bold" size="10" color="#FFD700">■</font>'
                '&nbsp;&nbsp;'
                '<font name="Helvetica-Bold" size="11" color="#111111">DATOS DE LA FACTURA</font>',
                ParagraphStyle("SecHead", leading=14),
            )
        ]],
        colWidths=[COL_TOTAL],
    )
    seccion_titulo.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elementos.append(seccion_titulo)

    # Formatear el total con 2 decimales
    total_formateado = f"${float(factura.total):,.2f}"
    num_factura = f"{settings.EMISOR_ESTABLECIMIENTO}-{settings.EMISOR_PUNTO_EMISION}-{factura.secuencial}"

    # Cuadro de datos del cliente con fondo gris claro y bordes finos
    info_pairs = [
        ("N° Factura", num_factura, "Fecha de Emisión", str(factura.fecha_emision)),
        ("Secuencial", str(factura.secuencial), "Estado SRI", str(factura.estado_sri)),
        ("Identificación Cliente", str(factura.identificacion_cliente), "Establecimiento",
         f"{settings.EMISOR_ESTABLECIMIENTO}-{settings.EMISOR_PUNTO_EMISION}"),
    ]

    datos_rows = []
    for label1, val1, label2, val2 in info_pairs:
        datos_rows.append([
            Paragraph(f'<font name="Helvetica" size="8" color="#555555">{label1}</font>', estilo_campo_label),
            Paragraph(f'<font name="Helvetica-Bold" size="10" color="#1A1A1A">{val1}</font>', estilo_campo_valor),
            Paragraph(f'<font name="Helvetica" size="8" color="#555555">{label2}</font>', estilo_campo_label),
            Paragraph(f'<font name="Helvetica-Bold" size="10" color="#1A1A1A">{val2}</font>', estilo_campo_valor),
        ])

    col_w = COL_TOTAL / 4
    tabla_datos = Table(datos_rows, colWidths=[col_w, col_w, col_w, col_w])
    tabla_datos.setStyle(
        TableStyle(
            [
                # Fondo gris muy claro para todo el cuadro
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_FONDO_GRIS),
                # Bordes finos y elegantes
                ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDE_GRIS),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, COLOR_BORDE_GRIS),
                ("LINEAFTER", (1, 0), (1, -1), 0.4, COLOR_BORDE_GRIS),
                # Padding
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 8 * mm))

    # ═══════════════════════════════════════════════════════
    # ─── TABLA DE TOTALES ─────────────────────────────────
    # ═══════════════════════════════════════════════════════
    seccion_totales = Table(
        [[
            Paragraph(
                '<font name="Helvetica-Bold" size="10" color="#FFD700">■</font>'
                '&nbsp;&nbsp;'
                '<font name="Helvetica-Bold" size="11" color="#111111">DETALLE FINANCIERO</font>',
                ParagraphStyle("SecTot", leading=14),
            )
        ]],
        colWidths=[COL_TOTAL],
    )
    seccion_totales.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elementos.append(seccion_totales)

    # Header de tabla negro con letras amarillas/blancas
    totales_header = ["Concepto", "Valor"]
    subtotal_val = float(factura.total) / 1.15  # Estimación del subtotal (antes de IVA 15%)
    iva_val = float(factura.total) - subtotal_val

    totales_data = [
        totales_header,
        ["Subtotal (Sin IVA)", f"${subtotal_val:,.2f}"],
        ["IVA (15%)", f"${iva_val:,.2f}"],
        ["TOTAL A PAGAR", total_formateado],
    ]

    tabla_totales = Table(totales_data, colWidths=[COL_TOTAL * 0.6, COL_TOTAL * 0.4])
    tabla_totales.setStyle(
        TableStyle(
            [
                # ─ Header negro con texto amarillo
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_NEGRO),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_AMARILLO),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                # ─ Filas de datos normales
                ("FONTNAME", (0, 1), (0, 2), "Helvetica"),
                ("FONTNAME", (1, 1), (1, 2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, 2), 10),
                ("TEXTCOLOR", (0, 1), (-1, 2), COLOR_TEXTO_OSCURO),
                ("TOPPADDING", (0, 1), (-1, 2), 8),
                ("BOTTOMPADDING", (0, 1), (-1, 2), 8),
                ("LINEBELOW", (0, 1), (-1, 2), 0.3, COLOR_BORDE_GRIS),
                # ─ Fondo alterno en filas
                ("BACKGROUND", (0, 1), (-1, 1), COLOR_FILA_ALT),
                ("BACKGROUND", (0, 2), (-1, 2), COLOR_BLANCO),
                # ─ Fila TOTAL A PAGAR: Fondo AMARILLO, texto NEGRO, BOLD
                ("BACKGROUND", (0, 3), (-1, 3), COLOR_AMARILLO),
                ("TEXTCOLOR", (0, 3), (-1, 3), COLOR_NEGRO),
                ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
                ("FONTSIZE", (0, 3), (-1, 3), 13),
                ("TOPPADDING", (0, 3), (-1, 3), 12),
                ("BOTTOMPADDING", (0, 3), (-1, 3), 12),
                # ─ Estilo general
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_NEGRO),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    elementos.append(tabla_totales)
    elementos.append(Spacer(1, 10 * mm))

    # ═══════════════════════════════════════════════════════
    # ─── CLAVE DE ACCESO ──────────────────────────────────
    # ═══════════════════════════════════════════════════════
    # Línea separadora fina
    sep = Table([[""]], colWidths=[COL_TOTAL], rowHeights=[0.5 * mm])
    sep.setStyle(
        TableStyle([("BACKGROUND", (0, 0), (-1, -1), COLOR_BORDE_GRIS)])
    )
    elementos.append(sep)
    elementos.append(Spacer(1, 5 * mm))

    seccion_clave = Table(
        [[
            Paragraph(
                '<font name="Helvetica-Bold" size="10" color="#FFD700">■</font>'
                '&nbsp;&nbsp;'
                '<font name="Helvetica-Bold" size="11" color="#111111">CLAVE DE ACCESO</font>',
                ParagraphStyle("SecClave", leading=14),
            )
        ]],
        colWidths=[COL_TOTAL],
    )
    seccion_clave.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elementos.append(seccion_clave)

    # Formatear clave en bloques de 8 para legibilidad
    clave = factura.clave_acceso
    clave_formateada = " ".join(
        [clave[i : i + 8] for i in range(0, len(clave), 8)]
    )

    # Clave dentro de un cuadro con borde
    clave_table = Table(
        [[Paragraph(clave_formateada, estilo_clave)]],
        colWidths=[COL_TOTAL],
    )
    clave_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_FONDO_GRIS),
                ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDE_GRIS),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    elementos.append(clave_table)
    elementos.append(Spacer(1, 6 * mm))

    # ═══════════════════════════════════════════════════════
    # ─── CÓDIGO QR ────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    qr_buffer = _generar_qr(factura.clave_acceso)
    qr_image = Image(qr_buffer, width=3.5 * cm, height=3.5 * cm)
    qr_image.hAlign = "CENTER"

    # QR con etiqueta debajo
    qr_label = Paragraph(
        '<font name="Helvetica" size="7" color="#999999">'
        'Escanea para verificar</font>',
        ParagraphStyle("QRLabel", alignment=1, leading=10),
    )

    qr_container = Table(
        [[qr_image], [qr_label]],
        colWidths=[COL_TOTAL],
    )
    qr_container.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(qr_container)
    elementos.append(Spacer(1, 6 * mm))

    # ═══════════════════════════════════════════════════════
    # ─── DISCLAIMER / PIE DE PÁGINA ───────────────────────
    # ═══════════════════════════════════════════════════════
    elementos.append(sep)
    elementos.append(Spacer(1, 3 * mm))

    estado_texto = factura.estado_sri
    if estado_texto == "SIMULADO":
        disclaimer = (
            "⚠ DOCUMENTO GENERADO EN MODO SIMULACIÓN — "
            "No válido como comprobante fiscal. "
            "Para validez tributaria, firme con certificado electrónico del SRI."
        )
    else:
        disclaimer = (
            "Representación Impresa del Documento Electrónico (RIDE). "
            "Este documento es una representación gráfica del comprobante electrónico. "
            "Consulte la validez en: https://srienlinea.sri.gob.ec"
        )

    # Disclaimer en un cuadro amarillo suave si es simulado
    if estado_texto == "SIMULADO":
        disclaimer_style = ParagraphStyle(
            "DisclaimerSim",
            fontSize=7,
            textColor=COLOR_NEGRO,
            fontName="Helvetica-Bold",
            alignment=1,
            leading=10,
        )
        disc_table = Table(
            [[Paragraph(disclaimer, disclaimer_style)]],
            colWidths=[COL_TOTAL],
        )
        disc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_AMARILLO_SUAVE),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_AMARILLO),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("ROUNDEDCORNERS", [3, 3, 3, 3]),
                ]
            )
        )
        elementos.append(disc_table)
    else:
        elementos.append(Paragraph(disclaimer, estilo_disclaimer))

    elementos.append(Spacer(1, 2 * mm))

    timestamp = ""
    if factura.created_at:
        timestamp = factura.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    elementos.append(
        Paragraph(
            f"Generado: {timestamp} &nbsp;|&nbsp; ID interno: {factura.id}",
            estilo_disclaimer,
        )
    )

    # ─── Barra inferior negra con texto amarillo ─────────
    elementos.append(Spacer(1, 6 * mm))
    footer_bar = Table(
        [[
            Paragraph(
                f'<font name="Helvetica" size="7" color="#FFD700">'
                f'{settings.EMISOR_NOMBRE_COMERCIAL} &nbsp;•&nbsp; '
                f'RUC: {settings.EMISOR_RUC} &nbsp;•&nbsp; '
                f'Sistema de Facturación Electrónica</font>',
                ParagraphStyle("Footer", alignment=1, leading=10),
            )
        ]],
        colWidths=[COL_TOTAL],
    )
    footer_bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_NEGRO_HEADER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    elementos.append(footer_bar)

    # ── Construir PDF ────────────────────────────────────
    doc.build(elementos)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(
        "RIDE PDF generado — factura id=%d, secuencial=%s (%d bytes)",
        factura.id,
        factura.secuencial,
        len(pdf_bytes),
    )

    return pdf_bytes
