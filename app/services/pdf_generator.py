"""
Generador de RIDE (Representación Impresa del Documento Electrónico).

Produce un PDF estético con los datos clave de la factura electrónica,
listo para enviar por WhatsApp o imprimir.

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

# ── Paleta de colores corporativa ────────────────────────
COLOR_PRIMARIO = colors.HexColor("#1a1a2e")
COLOR_ACENTO = colors.HexColor("#e94560")
COLOR_FONDO_HEADER = colors.HexColor("#16213e")
COLOR_FONDO_FILA = colors.HexColor("#f5f5f5")
COLOR_TEXTO_CLARO = colors.white
COLOR_BORDE = colors.HexColor("#cccccc")


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
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
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
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    # ── Estilos ──────────────────────────────────────────
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloRIDE",
        parent=styles["Title"],
        fontSize=18,
        textColor=COLOR_PRIMARIO,
        spaceAfter=2 * mm,
        fontName="Helvetica-Bold",
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloRIDE",
        parent=styles["Normal"],
        fontSize=11,
        textColor=COLOR_ACENTO,
        spaceAfter=4 * mm,
        fontName="Helvetica-Bold",
    )

    estilo_normal = ParagraphStyle(
        "NormalRIDE",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#333333"),
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

    # ── Elementos del PDF ────────────────────────────────
    elementos = []

    # ─── Header ──────────────────────────────────────────
    header_data = [
        [
            Paragraph(
                "COMPROBANTE ELECTRÓNICO",
                ParagraphStyle(
                    "HeaderLeft",
                    fontSize=14,
                    textColor=COLOR_TEXTO_CLARO,
                    fontName="Helvetica-Bold",
                ),
            ),
            Paragraph(
                "RIDE",
                ParagraphStyle(
                    "HeaderRight",
                    fontSize=14,
                    textColor=COLOR_ACENTO,
                    fontName="Helvetica-Bold",
                    alignment=2,
                ),
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[12 * cm, 5 * cm])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_FONDO_HEADER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (0, 0), 15),
                ("RIGHTPADDING", (-1, -1), (-1, -1), 15),
                ("ROUNDEDCORNERS", [6, 6, 0, 0]),
            ]
        )
    )
    elementos.append(header_table)

    # ─── Barra de acento ─────────────────────────────────
    barra = Table([[""]], colWidths=[17 * cm], rowHeights=[3 * mm])
    barra.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_ACENTO),
                ("ROUNDEDCORNERS", [0, 0, 0, 0]),
            ]
        )
    )
    elementos.append(barra)
    elementos.append(Spacer(1, 6 * mm))

    # ─── Datos del Emisor ────────────────────────────────
    elementos.append(
        Paragraph(settings.EMISOR_RAZON_SOCIAL, estilo_titulo)
    )
    elementos.append(
        Paragraph(
            f"{settings.EMISOR_NOMBRE_COMERCIAL} &nbsp;|&nbsp; RUC: {settings.EMISOR_RUC}",
            estilo_subtitulo,
        )
    )
    elementos.append(
        Paragraph(
            f"Dirección: {settings.EMISOR_DIR_ESTABLECIMIENTO} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Establecimiento: {settings.EMISOR_ESTABLECIMIENTO}-{settings.EMISOR_PUNTO_EMISION}",
            estilo_normal,
        )
    )
    elementos.append(Spacer(1, 6 * mm))

    # ─── Separador ───────────────────────────────────────
    sep = Table([[""]], colWidths=[17 * cm], rowHeights=[0.5 * mm])
    sep.setStyle(
        TableStyle([("BACKGROUND", (0, 0), (-1, -1), COLOR_BORDE)])
    )
    elementos.append(sep)
    elementos.append(Spacer(1, 6 * mm))

    # ─── Datos de la Factura ─────────────────────────────
    elementos.append(
        Paragraph("DATOS DE LA FACTURA", estilo_subtitulo)
    )

    # Formatear el total con 2 decimales
    total_formateado = f"${float(factura.total):,.2f}"

    factura_data = [
        ["Campo", "Valor"],
        ["N° Factura", f"{settings.EMISOR_ESTABLECIMIENTO}-{settings.EMISOR_PUNTO_EMISION}-{factura.secuencial}"],
        ["Secuencial", factura.secuencial],
        ["Fecha de Emisión", factura.fecha_emision],
        ["Identificación Cliente", factura.identificacion_cliente],
        ["Importe Total", total_formateado],
        ["Estado SRI", factura.estado_sri],
    ]

    tabla_factura = Table(factura_data, colWidths=[6 * cm, 11 * cm])
    tabla_factura.setStyle(
        TableStyle(
            [
                # Header de la tabla
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_TEXTO_CLARO),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                # Filas alternas
                ("BACKGROUND", (0, 1), (-1, 1), COLOR_FONDO_FILA),
                ("BACKGROUND", (0, 3), (-1, 3), COLOR_FONDO_FILA),
                ("BACKGROUND", (0, 5), (-1, 5), COLOR_FONDO_FILA),
                # Estilo general
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    elementos.append(tabla_factura)
    elementos.append(Spacer(1, 8 * mm))

    # ─── Clave de Acceso ─────────────────────────────────
    elementos.append(sep)
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(
        Paragraph("CLAVE DE ACCESO", estilo_subtitulo)
    )

    # Formatear clave en bloques de 8 para legibilidad
    clave = factura.clave_acceso
    clave_formateada = " ".join(
        [clave[i : i + 8] for i in range(0, len(clave), 8)]
    )

    estilo_clave = ParagraphStyle(
        "ClaveAcceso",
        parent=styles["Normal"],
        fontSize=11,
        textColor=COLOR_PRIMARIO,
        fontName="Courier-Bold",
        alignment=1,
        spaceAfter=4 * mm,
    )
    elementos.append(Paragraph(clave_formateada, estilo_clave))

    # ─── Código QR ───────────────────────────────────────
    qr_buffer = _generar_qr(factura.clave_acceso)
    qr_image = Image(qr_buffer, width=3.5 * cm, height=3.5 * cm)
    qr_image.hAlign = "CENTER"
    elementos.append(qr_image)
    elementos.append(Spacer(1, 6 * mm))

    # ─── Disclaimer ──────────────────────────────────────
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
