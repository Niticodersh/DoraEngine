"""Publication-style PDF export for DoraEngine research papers."""
from __future__ import annotations

import html
import io
import os
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.export_utils import markdown_soup, paragraph_html, references_table_data, sanitize_text, table_matrix

_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_ITALIC = "Helvetica-Oblique"


def _register_fonts() -> None:
    global _FONT_REGULAR, _FONT_BOLD, _FONT_ITALIC
    fonts = {
        "Arial": r"C:\Windows\Fonts\arial.ttf",
        "Arial-Bold": r"C:\Windows\Fonts\arialbd.ttf",
        "Arial-Italic": r"C:\Windows\Fonts\ariali.ttf",
    }
    if all(os.path.exists(path) for path in fonts.values()):
        for name, path in fonts.items():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, path))
        _FONT_REGULAR = "Arial"
        _FONT_BOLD = "Arial-Bold"
        _FONT_ITALIC = "Arial-Italic"


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle",
            parent=base["Title"],
            fontName=_FONT_BOLD,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=12,
        ),
        "meta": ParagraphStyle(
            "PaperMeta",
            parent=base["Normal"],
            fontName=_FONT_REGULAR,
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "PaperSection",
            parent=base["Heading2"],
            fontName=_FONT_BOLD,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111827"),
            spaceBefore=14,
            spaceAfter=7,
        ),
        "subsection": ParagraphStyle(
            "PaperSubsection",
            parent=base["Heading3"],
            fontName=_FONT_BOLD,
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "PaperBody",
            parent=base["BodyText"],
            fontName=_FONT_REGULAR,
            fontSize=10.5,
            leading=15.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "PaperBullet",
            parent=base["BodyText"],
            fontName=_FONT_REGULAR,
            fontSize=10.5,
            leading=15,
            leftIndent=14,
            firstLineIndent=-10,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=5,
        ),
        "blockquote": ParagraphStyle(
            "PaperQuote",
            parent=base["Italic"],
            fontName=_FONT_ITALIC,
            fontSize=10.5,
            leading=15,
            leftIndent=14,
            rightIndent=8,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=8,
        ),
        "reference": ParagraphStyle(
            "PaperReference",
            parent=base["BodyText"],
            fontName=_FONT_REGULAR,
            fontSize=10.5,
            leading=15,
            leftIndent=14,          # indentation like papers
            firstLineIndent=-14,    # hanging indent 🔥
            spaceAfter=6,
            textColor=colors.HexColor("#1F2937"),
        ),
    }


def _divider() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D1D5DB"), spaceBefore=6, spaceAfter=10)


def _table_flow(data: list[list[str]], styles: dict) -> Table:
    if not data or not data[0]:
        return Table(data)

    # Convert texts to Paragraphs for text wrapping
    wrapped_data = []
    
    cell_style = styles["body"].clone("TableCell")
    cell_style.fontSize = 9
    cell_style.leading = 12
    cell_style.alignment = 0 # TA_LEFT
    cell_style.spaceAfter = 0
    cell_style.spaceBefore = 0
    
    header_style = cell_style.clone("TableHeader")
    header_style.fontName = _FONT_BOLD
    header_style.textColor = colors.HexColor("#111827")
    
    for row_idx, row in enumerate(data):
        wrapped_row = []
        for cell_text in row:
            style = header_style if row_idx == 0 else cell_style
            text = html.escape(str(cell_text))
            wrapped_row.append(Paragraph(text, style))
        wrapped_data.append(wrapped_row)

    # A4 width = 595.27. Margins = 2.1cm (59.5) * 2 = 119. Usable = 476.27
    usable_width = 476.27
    col_width = usable_width / len(data[0])

    table = Table(wrapped_data, colWidths=[col_width] * len(data[0]), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9CA3AF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _watermark(canvas, watermark_text: str | None) -> None:
    if not watermark_text:
        return
    canvas.saveState()
    canvas.setFont(_FONT_BOLD, 34)
    canvas.setFillColor(colors.Color(0.75, 0.75, 0.75, alpha=0.18))
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, sanitize_text(watermark_text))
    canvas.restoreState()


def generate_pdf(
    query: str,
    answer: str,
    sources: list[dict],
    confidence: float = 0.0,
    timestamp: Optional[str] = None,
    watermark_text: str | None = None,
) -> bytes:
    _register_fonts()
    buffer = io.BytesIO()
    ts = timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.1 * cm,
        rightMargin=2.1 * cm,
        topMargin=1.9 * cm,
        bottomMargin=1.8 * cm,
    )

    story = [
        Paragraph(sanitize_text(query), styles["title"]),
        Paragraph(f"DoraEngine Research Paper | Confidence {int(confidence * 100)}% | {sanitize_text(ts)}", styles["meta"]),
        _divider(),
    ]

    root = markdown_soup(answer).find("div")
    for tag in root.children:
        if not getattr(tag, "name", None):
            continue
        name = tag.name.lower()
        if name in {"h1", "h2"}:
            story.append(Paragraph(paragraph_html(tag), styles["section"]))
        elif name == "h3":
            story.append(Paragraph(paragraph_html(tag), styles["subsection"]))
        elif name == "p":
            html_text = paragraph_html(tag)
            if html_text:
                story.append(Paragraph(html_text, styles["body"]))
        elif name in {"ul", "ol"}:
            for idx, item in enumerate(tag.find_all("li", recursive=False), 1):
                prefix = "•" if name == "ul" else f"{idx}."
                story.append(Paragraph(f"{prefix} {paragraph_html(item)}", styles["bullet"]))
        elif name == "table":
            data = table_matrix(tag)
            if data:
                story.append(Spacer(1, 4))
                story.append(_table_flow(data, styles))
                story.append(Spacer(1, 8))
        elif name == "blockquote":
            story.append(Paragraph(paragraph_html(tag), styles["blockquote"]))

    if sources:
        # story.extend([_divider(), Paragraph("References", styles["section"]), _table_flow(references_table_data(sources))])
        story.append(_divider())
        story.append(Paragraph("References", styles["section"]))

        for i, src in enumerate(sources, 1):
            title = sanitize_text(src.get("title", ""))
            domain = sanitize_text(src.get("domain", ""))
            url = sanitize_text(src.get("url", ""))

            ref_text = f"[{i}] {title}. {domain}. {url}"
            story.append(Paragraph(ref_text, styles["reference"]))
            story.append(Spacer(1, 6))

    def decorate(canvas, current_doc):
        _watermark(canvas, watermark_text)

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
