import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# ── Colour palette ─────────────────────────────────────────────────────────────
DARK_BLUE = colors.HexColor("#16213e")
ACCENT = colors.HexColor("#e94560")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
MID_GRAY = colors.HexColor("#555555")


def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "h1": ParagraphStyle(
            "H1Custom",
            parent=base["Heading1"],
            fontSize=16,
            textColor=DARK_BLUE,
            spaceAfter=4,
            spaceBefore=18,
            borderPad=4,
        ),
        "h2": ParagraphStyle(
            "H2Custom",
            parent=base["Heading2"],
            fontSize=13,
            textColor=ACCENT,
            spaceAfter=3,
            spaceBefore=10,
        ),
        "h3": ParagraphStyle(
            "H3Custom",
            parent=base["Heading3"],
            fontSize=11,
            textColor=MID_GRAY,
            spaceAfter=2,
            spaceBefore=6,
        ),
        "body": ParagraphStyle(
            "BodyCustom",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#222222"),
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            leftIndent=14,
            bulletIndent=4,
            textColor=colors.HexColor("#222222"),
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "TitleCustom",
            parent=base["Title"],
            fontSize=22,
            textColor=DARK_BLUE,
            spaceAfter=6,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleCustom",
            parent=base["Normal"],
            fontSize=11,
            textColor=MID_GRAY,
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
    }
    return styles


def _safe(text: str) -> str:
    """Escape XML entities and convert markdown bold/italic to ReportLab tags."""
    text = escape(text)
    # Bold+italic  ***text***
    text = re.sub(r"\*{3}(.*?)\*{3}", r"<b><i>\1</i></b>", text)
    # Bold         **text**
    text = re.sub(r"\*{2}(.*?)\*{2}", r"<b>\1</b>", text)
    # Italic       *text*  or  _text_
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.*?)_", r"<i>\1</i>", text)
    # Inline code  `text`
    text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", text)
    return text


def _parse_table(lines: list, start: int):
    """
    Try to parse a markdown pipe table starting at `start`.
    Returns (table_flowable_or_None, next_line_index).
    """
    table_lines = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|"):
            table_lines.append(line)
            i += 1
        else:
            break

    if len(table_lines) < 2:
        return None, start

    rows = []
    for tl in table_lines:
        # Skip separator rows like |---|---|
        if re.match(r"^\|[-| :]+\|$", tl):
            continue
        cells = [c.strip() for c in tl.strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return None, start

    # Normalise row widths
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")

    # Style the table
    col_width = (A4[0] - 80) / max_cols
    table_data = []
    for r_idx, row in enumerate(rows):
        styled_row = []
        for cell in row:
            style = ParagraphStyle(
                "tc",
                fontSize=8,
                leading=11,
                textColor=colors.white if r_idx == 0 else colors.HexColor("#222"),
            )
            styled_row.append(Paragraph(_safe(cell), style))
        table_data.append(styled_row)

    tbl = Table(table_data, colWidths=[col_width] * max_cols, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl, i


def create_pdf(markdown_text: str, company_name: str = "") -> bytes:
    """
    Converts markdown report text into a polished PDF.
    Handles: H1/H2/H3 headers, bullet lists, bold/italic, pipe tables, paragraphs.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=40,
    )
    styles = _build_styles()
    flowables = []

    # Cover header
    if company_name:
        flowables.append(Spacer(1, 10))
        flowables.append(
            Paragraph(f"Enterprise AI Intelligence Report", styles["title"])
        )
        flowables.append(
            Paragraph(company_name, styles["subtitle"])
        )
        flowables.append(
            HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=16)
        )

    lines = markdown_text.split("\n")
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # ── Skip empty lines ──────────────────────────────────────────────────
        if not line:
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        # ── Pipe table ────────────────────────────────────────────────────────
        if line.startswith("|"):
            tbl, i = _parse_table(lines, i)
            if tbl:
                flowables.append(Spacer(1, 6))
                flowables.append(tbl)
                flowables.append(Spacer(1, 6))
            else:
                i += 1
            continue

        safe = _safe(line)

        # ── H1 ────────────────────────────────────────────────────────────────
        if re.match(r"^#{1}\s+", line) and not re.match(r"^#{2,}", line):
            text = re.sub(r"^#+\s+", "", line)
            flowables.append(Spacer(1, 8))
            flowables.append(
                HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=2)
            )
            flowables.append(Paragraph(_safe(text), styles["h1"]))
            i += 1
            continue

        # ── H2 ────────────────────────────────────────────────────────────────
        if re.match(r"^#{2}\s+", line) and not re.match(r"^#{3,}", line):
            text = re.sub(r"^#+\s+", "", line)
            flowables.append(Paragraph(_safe(text), styles["h2"]))
            i += 1
            continue

        # ── H3 ────────────────────────────────────────────────────────────────
        if re.match(r"^#{3}\s+", line):
            text = re.sub(r"^#+\s+", "", line)
            flowables.append(Paragraph(_safe(text), styles["h3"]))
            i += 1
            continue

        # ── Bullet (- or * or numbered) ───────────────────────────────────────
        if re.match(r"^[-*]\s+", line):
            text = re.sub(r"^[-*]\s+", "", line)
            flowables.append(
                Paragraph(f"• {_safe(text)}", styles["bullet"])
            )
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            num = re.match(r"^(\d+)\.", line).group(1)
            flowables.append(
                Paragraph(f"{num}. {_safe(text)}", styles["bullet"])
            )
            i += 1
            continue

        # ── Horizontal rule ───────────────────────────────────────────────────
        if re.match(r"^---+$", line) or re.match(r"^\*\*\*+$", line):
            flowables.append(
                HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4)
            )
            i += 1
            continue

        # ── Regular paragraph ─────────────────────────────────────────────────
        flowables.append(Paragraph(safe, styles["body"]))
        i += 1

    doc.build(flowables)
    return buffer.getvalue()