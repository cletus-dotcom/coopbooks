"""PDF generation for BIR CAS documentation and books of accounts."""

import io
import re
from io import BytesIO
from pathlib import Path

from flask import g
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.accounting_service import (
    general_journal_book,
    general_ledger_accounts,
    member_subsidiary_ledger,
    trial_balance,
)
from app.bir_cas_config import SYSTEM_NAME, SYSTEM_VERSION
from app.bir_cas_service import pdf_data_for_slug
from app.models import local_time
from app.tenant_manager import get_coop_registry, get_current_coop

BIR_BOOK_TYPES = frozenset({
    "general-journal",
    "general-ledger",
    "trial-balance",
    "member-subsidiary",
    "audit-trail",
})

BIR_BOOK_TITLES = {
    "general-journal": "General Journal",
    "general-ledger": "General Ledger",
    "trial-balance": "Trial Balance",
    "member-subsidiary": "Member Subsidiary Ledger",
    "audit-trail": "System Audit Trail",
}

HEADER_TOP_OFFSET = 0.38 * inch
HEADER_LINE_HEIGHT = 11
HEADER_GAP_AFTER_SEP = 0.06 * inch
HEADER_LOGO_COL_WIDTH = 0.95 * inch
HEADER_RIGHT_COL_WIDTH = 2.05 * inch
RASTER_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor("#1B5E20"),
    ))
    styles.add(ParagraphStyle(
        name="SectionHead",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#0D3B12"),
    ))
    styles.add(ParagraphStyle(
        name="SmallCenter",
        parent=styles["Normal"],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name="CellText",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="CellText8",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    ))
    return styles


def _short_date(value):
    """Format ISO date/datetime strings as MM/DD/YYYY."""
    if not value:
        return ""
    if hasattr(value, "strftime"):
        if hasattr(value, "hour"):
            return value.strftime("%m/%d/%Y %H:%M")
        return value.strftime("%m/%d/%Y")
    text = str(value).strip()
    if not text:
        return ""
    if "T" in text:
        text = text.split("T", 1)[0]
    if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
        year, month, day = text[:10].split("-")
        return f"{month}/{day}/{year}"
    return text[:10]


def _escape_xml(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell_para(text, styles, style_name="CellText"):
    return Paragraph(_escape_xml(text) or " ", styles[style_name])


def _truncate_to_width(canvas, text, font_name, font_size, max_width):
    text = (text or "").strip()
    if not text:
        return ""
    canvas.setFont(font_name, font_size)
    if canvas.stringWidth(text, font_name, font_size) <= max_width:
        return text
    ellipsis = "..."
    while text and canvas.stringWidth(text + ellipsis, font_name, font_size) > max_width:
        text = text[:-1]
    return (text + ellipsis) if text else ellipsis


def _header_row_count(header_ctx, center_wrap_chars=48):
    addr_lines = len(_wrap_text(header_ctx["address"], center_wrap_chars)[:3])
    center_rows = 1 + addr_lines
    right_rows = max(len(header_ctx["contact_lines"]), 1)
    logo_rows = 4 if header_ctx.get("logo_path") else 0
    return max(center_rows, right_rows, logo_rows)


def _header_layout_for_margins(left_margin, right_margin):
    page_w, _ = letter
    left = left_margin
    right = page_w - right_margin
    usable = right - left
    logo_w = min(HEADER_LOGO_COL_WIDTH, usable * 0.16)
    right_w = min(HEADER_RIGHT_COL_WIDTH, usable * 0.30)
    center_w = usable - logo_w - right_w
    return {
        "left": left,
        "right": right,
        "logo_w": logo_w,
        "center_w": center_w,
        "right_w": right_w,
        "center_x": left + logo_w + (center_w / 2.0),
        "center_wrap_chars": max(36, int(center_w / 6.5)),
    }


def _header_layout(doc):
    return _header_layout_for_margins(doc.leftMargin, doc.rightMargin)


def _book_top_margin(header_ctx, left_margin=0.75 * inch, right_margin=0.75 * inch):
    layout = _header_layout_for_margins(left_margin, right_margin)
    rows = _header_row_count(header_ctx, layout["center_wrap_chars"])
    line_h = HEADER_LINE_HEIGHT / 72.0 * inch
    return HEADER_TOP_OFFSET + rows * line_h + HEADER_GAP_AFTER_SEP


def _active_registry():
    return get_coop_registry()


def _resolve_logo_path(registry):
    if registry and registry.logo_data:
        ext = (registry.logo_filename or "").rsplit(".", 1)[-1].lower()
        if ext in RASTER_LOGO_EXTENSIONS or ext == "svg":
            return BytesIO(registry.logo_data)
    return None


def _wrap_text(text, max_chars):
    words = (text or "").split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _coop_header_context():
    coop = get_current_coop()
    registry = _active_registry()
    name = coop.name if coop else SYSTEM_NAME
    address = (getattr(coop, "address", None) or "").strip()
    tin = (getattr(coop, "tin", None) or "").strip()
    rdo = (getattr(coop, "rdo", None) or "").strip()
    registration_no = (getattr(coop, "registration_no", None) or "").strip()
    contact_email = (getattr(coop, "contact_email", None) or "").strip()
    if not contact_email and registry:
        contact_email = (registry.contact_email or "").strip()

    contact_lines = []
    if registration_no:
        contact_lines.append(f"CDA Reg. No.: {registration_no}")
    if contact_email:
        contact_lines.append(f"Email: {contact_email}")
    if rdo:
        contact_lines.append(f"RDO: {rdo}")
    if tin:
        contact_lines.append(f"TIN: {tin}")

    return {
        "name": name,
        "address": address,
        "contact_lines": contact_lines,
        "logo_path": _resolve_logo_path(registry),
    }


def _draw_bir_book_header(canvas, doc, header_ctx):
    """Three-column coop header + separator line (repeated every page)."""
    canvas.saveState()
    page_w, page_h = letter
    layout = _header_layout(doc)
    left = layout["left"]
    right = layout["right"]
    logo_col_w = layout["logo_w"]
    center_col_w = layout["center_w"]
    right_col_w = layout["right_w"]
    center_x = layout["center_x"]
    center_wrap = layout["center_wrap_chars"]
    max_center_w = center_col_w - 12
    max_right_w = right_col_w - 8
    max_logo_w = logo_col_w - 6
    header_top = page_h - HEADER_TOP_OFFSET
    lowest_y = header_top - 12

    logo_path = header_ctx.get("logo_path")
    if logo_path:
        logo_h = min(0.58 * inch, _header_row_count(header_ctx, center_wrap) * (HEADER_LINE_HEIGHT / 72.0 * inch))
        try:
            from reportlab.lib.utils import ImageReader

            canvas.drawImage(
                ImageReader(logo_path),
                left,
                header_top,
                width=max_logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                anchor="nw",
                anchorAtXY=True,
            )
            lowest_y = min(lowest_y, header_top - logo_h)
        except Exception:
            pass

    name_y = header_top - 12
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#1B5E20"))
    name = _truncate_to_width(canvas, header_ctx["name"], "Helvetica-Bold", 11, max_center_w)
    canvas.drawCentredString(center_x, name_y, name)
    lowest_y = min(lowest_y, name_y - 2)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.black)
    addr_y = name_y - 13
    for line in _wrap_text(header_ctx["address"], center_wrap)[:3]:
        line = _truncate_to_width(canvas, line, "Helvetica", 8, max_center_w)
        canvas.drawCentredString(center_x, addr_y, line)
        lowest_y = min(lowest_y, addr_y - 2)
        addr_y -= HEADER_LINE_HEIGHT

    canvas.setFont("Helvetica", 7.5)
    contact_y = header_top - 12
    for line in header_ctx["contact_lines"]:
        line = _truncate_to_width(canvas, line, "Helvetica", 7.5, max_right_w)
        canvas.drawRightString(right, contact_y, line)
        lowest_y = min(lowest_y, contact_y - 2)
        contact_y -= HEADER_LINE_HEIGHT

    sep_y = lowest_y - 4
    canvas.setStrokeColor(colors.HexColor("#333333"))
    canvas.setLineWidth(0.5)
    canvas.line(left, sep_y, right, sep_y)
    canvas.restoreState()


def _bir_book_page(canvas, doc, header_ctx):
    _draw_bir_book_header(canvas, doc, header_ctx)
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _cas_header_footer(canvas, doc, title, coop_name):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch, letter[1] - 0.5 * inch, f"{coop_name} — {SYSTEM_NAME} v{SYSTEM_VERSION}")
    canvas.drawRightString(letter[0] - inch, letter[1] - 0.5 * inch, title)
    canvas.drawCentredString(letter[0] / 2, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def bir_book_pdf_filename(book_type):
    coop = get_current_coop()
    label = (coop.name if coop else "coop").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", label).strip("-")[:40] or "coop"
    return f"{slug}-{book_type}.pdf"


def render_cas_document_pdf(slug):
    data = pdf_data_for_slug(slug)
    if not data:
        return None

    coop = get_current_coop()
    coop_name = coop.name if coop else SYSTEM_NAME
    title = f"BIR CAS — {data['number']}. {data['title']}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = _styles()
    story = []

    story.append(Paragraph(title, styles["DocTitle"]))
    story.append(Paragraph(
        f"{data['generated_for']}<br/>Reference: {data['bir_reference']}",
        styles["Normal"],
    ))
    story.append(Paragraph(
        f"Generated: {_short_date(local_time())} (Asia/Manila)",
        styles["SmallCenter"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    for section_title, rows in data.get("sections", []):
        story.append(Paragraph(section_title, styles["SectionHead"]))
        if not rows:
            continue
        if isinstance(rows[0], dict):
            keys = list(rows[0].keys())
            table_data = [[k.replace("_", " ").title() for k in keys]]
            for row in rows:
                table_data.append([str(row.get(k, "")) for k in keys])
            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbf8")]),
            ]))
            story.append(t)
        story.append(Spacer(1, 0.15 * inch))

    if data.get("audit_rows"):
        story.append(Paragraph("Audit Trail (Recent Activity)", styles["SectionHead"]))
        audit_data = [["Date/Time", "User", "Action", "Entity", "Label"]]
        for row in data["audit_rows"][:50]:
            audit_data.append([
                _short_date(row["created_at"]),
                row["username"],
                row["action"],
                row["entity_type"],
                (row["entity_label"] or "")[:40],
            ])
        t = Table(audit_data, repeatRows=1, colWidths=[1.2 * inch, 1 * inch, 0.7 * inch, 1 * inch, 2 * inch])
        t.setStyle(_table_style())
        story.append(t)

    doc.build(
        story,
        onFirstPage=lambda c, d: _cas_header_footer(c, d, title, coop_name),
        onLaterPages=lambda c, d: _cas_header_footer(c, d, title, coop_name),
    )
    buffer.seek(0)
    return buffer


def render_book_pdf(book_type):
    if book_type not in BIR_BOOK_TYPES:
        raise ValueError(f"Unsupported book type: {book_type}")

    header_ctx = _coop_header_context()
    as_of = local_time().date()
    title = BIR_BOOK_TITLES[book_type]
    top_margin = _book_top_margin(header_ctx)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=top_margin,
        bottomMargin=0.75 * inch,
    )
    styles = _styles()
    story = []

    story.append(Paragraph(title, styles["DocTitle"]))
    story.append(Paragraph(
        f"As of {_short_date(as_of)} · Books of Accounts (BIR RR No. 9-2009)",
        styles["SmallCenter"],
    ))
    story.append(Spacer(1, 0.12 * inch))

    if book_type == "general-journal":
        _append_general_journal(story, styles)
    elif book_type == "general-ledger":
        _append_general_ledger(story, styles)
    elif book_type == "trial-balance":
        _append_trial_balance(story, styles)
    elif book_type == "member-subsidiary":
        _append_member_subsidiary(story, styles)
    elif book_type == "audit-trail":
        from app.audit_service import audit_trail_rows
        audit_data = [["Date/Time", "User", "Action", "Entity", "ID", "Description"]]
        for row in audit_trail_rows(limit=200):
            audit_data.append([
                _short_date(row["created_at"]),
                row["username"],
                row["action"],
                row["entity_type"],
                row["entity_id"],
                _cell_para((row["entity_label"] or "")[:80], styles),
            ])
        t = Table(
            audit_data,
            repeatRows=1,
            colWidths=[0.85 * inch, 0.85 * inch, 0.55 * inch, 0.85 * inch, 0.45 * inch, 3.45 * inch],
        )
        t.setStyle(_table_style(font_size=7))
        story.append(t)

    page_cb = lambda c, d, ctx=header_ctx: _bir_book_page(c, d, ctx)
    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)
    buffer.seek(0)
    return buffer


def _table_style(font_size=8):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbf8")]),
    ])


def _append_general_journal(story, styles):
    entries = general_journal_book()
    col_w = [
        0.62 * inch,
        0.62 * inch,
        1.25 * inch,
        2.05 * inch,
        0.72 * inch,
        0.72 * inch,
        1.02 * inch,
    ]
    data = [["Date", "Entry #", "Account", "Description", "Debit", "Credit", "Posted By"]]
    for entry in entries:
        for i, line in enumerate(entry["lines"]):
            desc = line["memo"] or entry["description"] if i == 0 else line["memo"] or ""
            data.append([
                _short_date(entry["entry_date"]) if i == 0 else "",
                entry["entry_no"] if i == 0 else "",
                _cell_para(f"{line['code']} {line['name']}", styles),
                _cell_para(desc, styles),
                f"{line['debit']:,.2f}" if line["debit"] else "",
                f"{line['credit']:,.2f}" if line["credit"] else "",
                _cell_para(entry["posted_by"] if i == 0 else "", styles),
            ])
    t = Table(data, repeatRows=1, colWidths=col_w)
    t.setStyle(_table_style(font_size=7))
    story.append(t)


def _append_general_ledger(story, styles):
    accounts = general_ledger_accounts()
    col_w = [0.72 * inch, 0.72 * inch, 1.65 * inch, 0.85 * inch, 0.85 * inch, 1.41 * inch]
    for acct in accounts:
        story.append(Paragraph(
            f"{acct['code']} — {acct['name']} ({acct['account_type']})",
            styles["SectionHead"],
        ))
        data = [["Date", "Entry #", "Reference", "Debit", "Credit", "Balance"]]
        for line in acct["lines"]:
            data.append([
                _short_date(line["entry_date"]),
                line["entry_no"],
                _cell_para(line["reference"] or "", styles),
                f"{line['debit']:,.2f}" if line["debit"] else "",
                f"{line['credit']:,.2f}" if line["credit"] else "",
                f"{line['balance']:,.2f}",
            ])
        data.append(["", "", "Ending Balance", "", "", f"{acct['ending_balance']:,.2f}"])
        t = Table(data, repeatRows=1, colWidths=col_w)
        t.setStyle(_table_style(font_size=7))
        story.append(t)
        story.append(Spacer(1, 0.1 * inch))


def _append_trial_balance(story, styles):
    rows = trial_balance()
    col_w = [0.62 * inch, 2.85 * inch, 0.95 * inch, 0.94 * inch, 0.94 * inch]
    data = [["Code", "Account", "Type", "Debit", "Credit"]]
    total_debit = total_credit = 0
    for row in rows:
        data.append([
            row["code"],
            _cell_para(row["name"], styles, "CellText8"),
            row["account_type"],
            f"{row['debit']:,.2f}" if row["debit"] else "",
            f"{row['credit']:,.2f}" if row["credit"] else "",
        ])
        total_debit += row["debit"]
        total_credit += row["credit"]
    data.append(["", "", "Totals", f"{total_debit:,.2f}", f"{total_credit:,.2f}"])
    t = Table(data, repeatRows=1, colWidths=col_w)
    t.setStyle(_table_style())
    story.append(t)


def _append_member_subsidiary(story, styles):
    ledgers = member_subsidiary_ledger()
    if not ledgers:
        story.append(Paragraph("No member ledger transactions recorded.", styles["Normal"]))
        return

    for ledger in ledgers:
        story.append(Paragraph(
            f"{ledger['member_no']} — {ledger['full_name']}",
            styles["SectionHead"],
        ))
        col_w = [
            0.62 * inch,
            0.88 * inch,
            0.58 * inch,
            1.35 * inch,
            0.72 * inch,
            0.72 * inch,
            1.13 * inch,
        ]
        data = [["Date", "Type", "Ledger", "Reference", "Debit", "Credit", "Posted By"]]
        for line in ledger["lines"]:
            data.append([
                _short_date(line["txn_date"]),
                _cell_para(line["txn_type"], styles),
                line["ledger_type"],
                _cell_para(line["reference"] or "", styles),
                f"{line['debit']:,.2f}" if line["debit"] else "",
                f"{line['credit']:,.2f}" if line["credit"] else "",
                _cell_para(line["posted_by"] or "", styles),
            ])
        data.append([
            "",
            "",
            "Balances",
            _cell_para(
                f"Share: {ledger['share_balance']:,.2f} · Savings: {ledger['savings_balance']:,.2f}",
                styles,
            ),
            "",
            "",
            "",
        ])
        t = Table(data, repeatRows=1, colWidths=col_w)
        t.setStyle(_table_style(font_size=7))
        story.append(t)
        story.append(Spacer(1, 0.1 * inch))
