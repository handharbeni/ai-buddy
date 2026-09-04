"""Output formatter service.

Converts query results into various output formats:
- JSON (raw data)
- CSV (spreadsheet)
- XLSX (Excel)
- DOCX (Word document with table)
- PDF (PDF report)
- Markdown (text with table)
- HTML (web view with table)
"""

import io
import csv
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── Format Helpers ─────────────────────────────────────────────────────────

def _to_table_data(data: List[Dict[str, Any]]) -> tuple[list, list]:
    """Extract columns and rows from list of dicts.
    Returns (columns, rows) where rows are list of values in column order.
    """
    if not data:
        return [], []

    # Preserve insertion order from first row
    columns = list(data[0].keys())

    # Add new columns from later rows
    for row in data[1:]:
        for key in row.keys():
            if key not in columns:
                columns.append(key)

    rows = []
    for row in data:
        rows.append([_format_cell(row.get(col, "")) for col in columns])

    return columns, rows


def _format_cell(value: Any) -> str:
    """Format a cell value for display."""
    if value is None:
        return ""
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"
    if isinstance(value, (int,)):
        return f"{value:,}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str):
        return value
    return str(value)


# ─── Format Generators ──────────────────────────────────────────────────────

def to_json(data: List[Dict[str, Any]], question: str = "", metadata: dict = None) -> bytes:
    """Output as pretty JSON."""
    payload = {
        "question": question,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "row_count": len(data),
        "data": data,
    }
    if metadata:
        payload["metadata"] = metadata
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def to_csv(data: List[Dict[str, Any]], question: str = "") -> bytes:
    """Output as CSV."""
    if not data:
        return b""
    columns, rows = _to_table_data(data)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel


def to_xlsx(data: List[Dict[str, Any]], question: str = "") -> bytes:
    """Output as Excel .xlsx."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Data"

    if not data:
        return _empty_xlsx(wb)

    columns, rows = _to_table_data(data)

    # Title row
    if question:
        ws.cell(row=1, column=1, value=question)
        ws.cell(row=1, column=1).font = Font(bold=True, size=14)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
        ws.row_dimensions[1].height = 22

        # Metadata row
        ws.cell(row=2, column=1, value=f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Rows: {len(data)}")
        ws.cell(row=2, column=1).font = Font(italic=True, size=9, color="666666")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(columns))
        header_start = 4
    else:
        header_start = 1

    # Header row
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    for col_idx, col in enumerate(columns, start=1):
        cell = ws.cell(row=header_start, column=col_idx, value=col.replace("_", " ").title())
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # Data rows
    for row_idx, row_data in enumerate(rows, start=header_start + 1):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = border
            # Alternating row colors
            if row_idx % 2 == 0:
                cell.fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")

    # Auto-size columns
    for col_idx, col in enumerate(columns, start=1):
        max_len = len(col)
        for row_data in rows:
            if col_idx - 1 < len(row_data):
                val_len = len(str(row_data[col_idx - 1]))
                if val_len > max_len:
                    max_len = val_len
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)

    # Freeze header
    ws.freeze_panes = ws.cell(row=header_start + 1, column=1)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _empty_xlsx(wb) -> bytes:
    from openpyxl import Workbook
    if not wb.sheetnames:
        wb.create_sheet("Data")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_docx(data: List[Dict[str, Any]], question: str = "", answer: str = "") -> bytes:
    """Output as Word document with table."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Title
    title = doc.add_heading("BAPENDA - Query Result", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Question
    if question:
        p = doc.add_paragraph()
        run = p.add_run("Pertanyaan: ")
        run.bold = True
        run.font.size = Pt(11)
        p.add_run(question).font.size = Pt(11)

    # Answer
    if answer:
        doc.add_paragraph()
        h = doc.add_heading("Jawaban", level=2)
        p = doc.add_paragraph(answer)
        for run in p.runs:
            run.font.size = Pt(11)

    # Data table
    if data:
        doc.add_paragraph()
        doc.add_heading(f"Data ({len(data)} baris)", level=2)

        columns, rows = _to_table_data(data)

        table = doc.add_table(rows=1, cols=len(columns))
        table.style = "Light Grid Accent 1"

        # Header
        hdr_cells = table.rows[0].cells
        for col_idx, col in enumerate(columns):
            cell = hdr_cells[col_idx]
            cell.text = col.replace("_", " ").title()
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(10)

        # Data rows
        for row_data in rows:
            row_cells = table.add_row().cells
            for col_idx, value in enumerate(row_data):
                if col_idx < len(row_cells):
                    row_cells[col_idx].text = str(value)

    # Footer
    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run(f"Generated by BAPENDA Local AI Platform | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    run.italic = True
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def to_pdf(data: List[Dict[str, Any]], question: str = "", answer: str = "") -> bytes:
    """Output as PDF report."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )

    buf = io.BytesIO()

    # Use landscape if many columns
    page_size = landscape(A4) if data and len(data[0]) > 5 else A4

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="BAPENDA Query Result",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], alignment=1)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"])

    elements = []

    # Title
    elements.append(Paragraph("BAPENDA - Query Result", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Question
    if question:
        q_style = ParagraphStyle("Q", parent=styles["Normal"], fontSize=11, spaceAfter=6)
        elements.append(Paragraph(f"<b>Pertanyaan:</b> {question}", q_style))

    # Answer
    if answer:
        a_style = ParagraphStyle("A", parent=styles["Normal"], fontSize=10, spaceAfter=12)
        elements.append(Paragraph("<b>Jawaban:</b>", h2_style))
        elements.append(Paragraph(answer, a_style))
        elements.append(Spacer(1, 0.3 * cm))

    # Data table
    if data:
        elements.append(Paragraph(f"<b>Data ({len(data)} baris)</b>", h2_style))
        elements.append(Spacer(1, 0.2 * cm))

        columns, rows = _to_table_data(data)
        # Truncate column names
        col_headers = [c.replace("_", " ").title()[:30] for c in columns]

        table_data = [col_headers] + rows

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ]))
        elements.append(t)

    # Footer
    elements.append(Spacer(1, 0.5 * cm))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey)
    elements.append(Paragraph(
        f"Generated by BAPENDA Local AI Platform | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        footer_style
    ))

    doc.build(elements)
    return buf.getvalue()


def to_markdown(data: List[Dict[str, Any]], question: str = "", answer: str = "") -> bytes:
    """Output as Markdown table."""
    lines = []
    if question:
        lines.append(f"# BAPENDA Query Result")
        lines.append(f"")
        lines.append(f"**Pertanyaan:** {question}")
        lines.append(f"")
    if answer:
        lines.append(f"## Jawaban")
        lines.append(f"")
        lines.append(answer)
        lines.append(f"")
    if data:
        lines.append(f"## Data ({len(data)} baris)")
        lines.append(f"")
        columns, rows = _to_table_data(data)
        # Header
        lines.append("| " + " | ".join(c.replace("_", " ") for c in columns) + " |")
        lines.append("|" + "|".join(["---"] * len(columns)) + "|")
        # Rows
        for row in rows:
            # Escape pipes
            escaped = [str(cell).replace("|", "\\|").replace("\n", " ") for cell in row]
            lines.append("| " + " | ".join(escaped) + " |")
    lines.append(f"")
    lines.append(f"*Generated by BAPENDA Local AI Platform | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*")
    return "\n".join(lines).encode("utf-8")


def to_html(data: List[Dict[str, Any]], question: str = "", answer: str = "") -> bytes:
    """Output as HTML page with table."""
    html = ['<!DOCTYPE html>', '<html><head>',
            '<meta charset="utf-8">',
            '<title>BAPENDA Query Result</title>',
            '<style>',
            'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; color: #1a202c; }',
            'h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 0.5rem; }',
            'h2 { color: #2d3748; margin-top: 2rem; }',
            '.question { background: #edf2f7; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }',
            '.answer { background: #f7fafc; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #2b6cb0; }',
            'table { border-collapse: collapse; width: 100%; margin: 1rem 0; }',
            'th { background: #1a365d; color: white; padding: 0.75rem; text-align: left; font-size: 0.875rem; }',
            'td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #e2e8f0; font-size: 0.875rem; }',
            'tr:nth-child(even) { background: #f7fafc; }',
            '.footer { margin-top: 2rem; color: #718096; font-size: 0.75rem; }',
            '</style></head><body>']

    html.append('<h1>BAPENDA - Query Result</h1>')
    if question:
        html.append(f'<div class="question"><strong>Pertanyaan:</strong> {question}</div>')
    if answer:
        html.append(f'<h2>Jawaban</h2>')
        html.append(f'<div class="answer">{answer}</div>')
    if data:
        html.append(f'<h2>Data ({len(data)} baris)</h2>')
        columns, rows = _to_table_data(data)
        html.append('<table>')
        html.append('<thead><tr>')
        for col in columns:
            html.append(f'<th>{col.replace("_", " ").title()}</th>')
        html.append('</tr></thead>')
        html.append('<tbody>')
        for row in rows:
            html.append('<tr>')
            for cell in row:
                html.append(f'<td>{cell}</td>')
            html.append('</tr>')
        html.append('</tbody></table>')
    html.append(f'<div class="footer">Generated by BAPENDA Local AI Platform | {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</div>')
    html.append('</body></html>')
    return "\n".join(html).encode("utf-8")


# ─── Format Dispatcher ──────────────────────────────────────────────────────

FORMATS = {
    "json": {"fn": to_json, "ext": "json", "mime": "application/json"},
    "csv": {"fn": to_csv, "ext": "csv", "mime": "text/csv"},
    "xlsx": {"fn": to_xlsx, "ext": "xlsx", "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "docx": {"fn": to_docx, "ext": "docx", "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "pdf": {"fn": to_pdf, "ext": "pdf", "mime": "application/pdf"},
    "md": {"fn": to_markdown, "ext": "md", "mime": "text/markdown"},
    "html": {"fn": to_html, "ext": "html", "mime": "text/html"},
}


def format_data(
    data: List[Dict[str, Any]],
    fmt: str,
    question: str = "",
    answer: str = "",
) -> tuple[bytes, str, str]:
    """Format data into requested format.

    Returns: (content_bytes, filename, mime_type)
    """
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format: {fmt}. Available: {list(FORMATS.keys())}")

    entry = FORMATS[fmt]
    # json only takes specific args
    if fmt == "json":
        content = entry["fn"](data, question=question, metadata={"answer": answer} if answer else None)
    elif fmt == "xlsx":
        # xlsx doesn't include answer in the sheet, only in metadata
        content = entry["fn"](data, question=question)
    elif fmt == "csv":
        content = entry["fn"](data, question=question)
    else:
        content = entry["fn"](data, question=question, answer=answer)

    # Build filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_q = "".join(c if c.isalnum() else "_" for c in (question or "result"))[:50]
    filename = f"bapenda_{safe_q}_{timestamp}.{entry['ext']}"

    return content, filename, entry["mime"]


def list_formats() -> List[Dict[str, str]]:
    """List available formats."""
    return [
        {"id": k, "ext": v["ext"], "mime": v["mime"]}
        for k, v in FORMATS.items()
    ]
