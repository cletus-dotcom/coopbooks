"""Excel template generation and cooperative data migration import."""

import io
import zipfile
from datetime import datetime
from decimal import Decimal, InvalidOperation

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from werkzeug.security import generate_password_hash

from app import db
from app.migration_config import IMPORT_ORDER, MIGRATION_TABLE_MAP, MIGRATION_TABLES
from app.models import (
    Account,
    Cooperative,
    JournalEntry,
    JournalLine,
    Member,
    MemberLedger,
    User,
    local_time,
)
from app.tenant_manager import switch_tenant_bind


def _header_style():
    return {
        "font": Font(bold=True, color="FFFFFF"),
        "fill": PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid"),
    }


def build_template_workbook(table_key):
    """Build a single-table Excel import template."""
    spec = MIGRATION_TABLE_MAP[table_key]
    wb = Workbook()
    ws = wb.active
    ws.title = spec["sheet"]

    style = _header_style()
    for col, header in enumerate(spec["headers"], start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = style["font"]
        cell.fill = style["fill"]

    if spec.get("example"):
        for col, value in enumerate(spec["example"], start=1):
            ws.cell(row=2, column=col, value=value)

    ws.freeze_panes = "A2"
    for col in range(1, len(spec["headers"]) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18

    notes = wb.create_sheet("_instructions")
    notes["A1"] = spec["label"]
    notes["A1"].font = Font(bold=True, size=12)
    notes["A3"] = "Description"
    notes["A4"] = spec["description"]
    notes["A6"] = "Required columns"
    notes["A7"] = ", ".join(spec.get("required", []))
    notes["A9"] = "Paste your data starting row 2 on the main sheet. Do not rename header row."

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def build_all_templates_zip():
    """Zip archive containing all migration templates."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for spec in IMPORT_ORDER:
            wb_buf = build_template_workbook(spec["key"])
            zf.writestr(spec["filename"], wb_buf.getvalue())
        readme = (
            "CoopBooks Migration Templates\n"
            "=============================\n\n"
            "Import order:\n"
        )
        for spec in IMPORT_ORDER:
            readme += f"  {spec['order']}. {spec['filename']} — {spec['label']}\n"
        readme += (
            "\nFill each sheet from row 2. Keep column headers unchanged.\n"
            "Upload via Platform Admin → Migration Tool.\n"
        )
        zf.writestr("README.txt", readme)
    buffer.seek(0)
    return buffer


def _parse_bool(value):
    if value is None or str(value).strip() == "":
        return True
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def _parse_decimal(value, default=0):
    if value is None or str(value).strip() == "":
        return Decimal(str(default))
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"Invalid number: {value}")


def _parse_date(value):
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value} (use YYYY-MM-DD)")


def _row_dict(headers, row_values):
    data = {}
    for i, header in enumerate(headers):
        if i < len(row_values):
            val = row_values[i]
            if val is not None and str(val).strip() != "":
                data[header] = val
    return data


def read_upload_rows(file_storage, table_key):
    """Parse uploaded Excel into list of row dicts."""
    spec = MIGRATION_TABLE_MAP[table_key]
    wb = load_workbook(file_storage, read_only=True, data_only=True)
    sheet_name = spec["sheet"]
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["File is empty."]

    headers = [str(h).strip() if h else "" for h in rows[0]]
    missing = [h for h in spec["headers"] if h not in headers]
    if missing:
        return [], [f"Missing columns: {', '.join(missing)}"]

    col_index = {h: headers.index(h) for h in spec["headers"]}
    parsed = []
    errors = []

    for row_num, row in enumerate(rows[1:], start=2):
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue
        values = [row[col_index[h]] if col_index[h] < len(row) else None for h in spec["headers"]]
        data = _row_dict(spec["headers"], values)
        for req in spec.get("required", []):
            if req not in data:
                errors.append(f"Row {row_num}: missing required '{req}'")
                break
        else:
            data["_row"] = row_num
            parsed.append(data)

    return parsed, errors


def validate_import(coop_slug, table_key, rows):
    """Dry-run validation without writing to database."""
    switch_tenant_bind(coop_slug)
    errors = []
    warnings = []

    if table_key == "journal_lines":
        entry_nos = {e.entry_no for e in JournalEntry.query.all()}
        codes = {a.code for a in Account.query.all()}
        for row in rows:
            if row.get("entry_no") not in entry_nos:
                errors.append(f"Row {row['_row']}: unknown entry_no '{row.get('entry_no')}'")
            if row.get("account_code") not in codes:
                errors.append(f"Row {row['_row']}: unknown account_code '{row.get('account_code')}'")

    if table_key == "member_ledger":
        member_nos = {m.member_no for m in Member.query.all()}
        for row in rows:
            if row.get("member_no") not in member_nos:
                errors.append(f"Row {row['_row']}: unknown member_no '{row.get('member_no')}'")

    return {"valid_rows": len(rows), "errors": errors, "warnings": warnings}


def import_rows(coop_slug, table_key, rows, mode="append"):
    """Import parsed rows into tenant database. mode: append | replace."""
    switch_tenant_bind(coop_slug)
    spec = MIGRATION_TABLE_MAP[table_key]
    imported = 0
    skipped = 0
    errors = []

    if mode == "replace":
        _clear_table(table_key)

    try:
        for row in rows:
            try:
                created = _import_one_row(table_key, row, mode)
                if created:
                    imported += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"Row {row.get('_row', '?')}: {exc}")

        if imported:
            db.session.commit()
        else:
            db.session.rollback()
    except Exception as exc:
        db.session.rollback()
        errors.append(str(exc))

    return {
        "table": spec["label"],
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


def _clear_table(table_key):
    if table_key == "member_ledger":
        MemberLedger.query.delete()
    elif table_key == "journal_lines":
        JournalLine.query.delete()
    elif table_key == "journal_entries":
        JournalEntry.query.delete()
    elif table_key == "members":
        MemberLedger.query.delete()
        Member.query.delete()
    elif table_key == "users":
        User.query.delete()
    elif table_key == "accounts":
        JournalLine.query.delete()
        JournalEntry.query.delete()
        Account.query.delete()
    elif table_key == "cooperatives":
        Cooperative.query.delete()
    db.session.flush()


def _import_one_row(table_key, row, mode):
    if table_key == "cooperatives":
        existing = Cooperative.query.first()
        if existing and mode == "append":
            existing.name = row.get("name", existing.name)
            existing.registration_no = row.get("registration_no") or existing.registration_no
            existing.tin = row.get("tin") or existing.tin
            existing.rdo = row.get("rdo") or existing.rdo
            existing.coop_type = row.get("coop_type") or existing.coop_type
            existing.address = row.get("address") or existing.address
            existing.fiscal_year_end = row.get("fiscal_year_end") or existing.fiscal_year_end
            return False
        if existing:
            return False
        db.session.add(Cooperative(
            name=row["name"],
            registration_no=row.get("registration_no"),
            tin=row.get("tin"),
            rdo=row.get("rdo"),
            coop_type=row.get("coop_type"),
            address=row.get("address"),
            fiscal_year_end=row.get("fiscal_year_end", "December 31"),
        ))
        return True

    if table_key == "accounts":
        if Account.query.filter_by(code=str(row["code"]).strip()).first():
            return False
        db.session.add(Account(
            code=str(row["code"]).strip(),
            name=str(row["name"]).strip(),
            account_type=str(row["account_type"]).strip(),
            category=row.get("category"),
            normal_balance=str(row["normal_balance"]).strip(),
            is_active=_parse_bool(row.get("is_active")),
        ))
        return True

    if table_key == "users":
        username = str(row["username"]).strip()
        if User.query.filter_by(username=username).first():
            return False
        db.session.add(User(
            username=username,
            full_name=row.get("full_name"),
            email=row.get("email"),
            role=str(row.get("role", "Member")).strip(),
            status=str(row.get("status", "Active")).strip(),
            password_hash=generate_password_hash(str(row["password"])),
        ))
        return True

    if table_key == "members":
        member_no = str(row["member_no"]).strip()
        if Member.query.filter_by(member_no=member_no).first():
            return False
        db.session.add(Member(
            member_no=member_no,
            full_name=str(row["full_name"]).strip(),
            email=row.get("email"),
            phone=row.get("phone"),
            address=row.get("address"),
            membership_date=_parse_date(row.get("membership_date")),
            share_capital=_parse_decimal(row.get("share_capital")),
            savings_balance=_parse_decimal(row.get("savings_balance")),
            status=str(row.get("status", "Active")).strip(),
        ))
        return True

    if table_key == "journal_entries":
        entry_no = str(row["entry_no"]).strip()
        if JournalEntry.query.filter_by(entry_no=entry_no).first():
            return False
        db.session.add(JournalEntry(
            entry_no=entry_no,
            entry_date=_parse_date(row["entry_date"]),
            description=row.get("description"),
            reference=row.get("reference"),
            posted_by=row.get("posted_by"),
        ))
        return True

    if table_key == "journal_lines":
        entry = JournalEntry.query.filter_by(entry_no=str(row["entry_no"]).strip()).first()
        account = Account.query.filter_by(code=str(row["account_code"]).strip()).first()
        if not entry or not account:
            raise ValueError("entry_no or account_code not found")
        db.session.add(JournalLine(
            entry_id=entry.id,
            account_id=account.id,
            debit=_parse_decimal(row.get("debit")),
            credit=_parse_decimal(row.get("credit")),
            memo=row.get("memo"),
        ))
        return True

    if table_key == "member_ledger":
        member = Member.query.filter_by(member_no=str(row["member_no"]).strip()).first()
        if not member:
            raise ValueError(f"member_no not found: {row.get('member_no')}")
        db.session.add(MemberLedger(
            member_id=member.id,
            txn_date=_parse_date(row["txn_date"]),
            txn_type=str(row["txn_type"]).strip(),
            ledger_type=str(row["ledger_type"]).strip(),
            reference=row.get("reference"),
            description=row.get("description"),
            debit=_parse_decimal(row.get("debit")),
            credit=_parse_decimal(row.get("credit")),
            posted_by=row.get("posted_by"),
        ))
        return True

    raise ValueError(f"Unknown table: {table_key}")


def import_batch(coop_slug, uploads, mode="append"):
    """Import multiple tables in dependency order."""
    results = []
    for spec in IMPORT_ORDER:
        key = spec["key"]
        if key not in uploads:
            continue
        rows, parse_errors = read_upload_rows(uploads[key], key)
        if parse_errors:
            results.append({
                "table": spec["label"],
                "imported": 0,
                "skipped": 0,
                "errors": parse_errors,
            })
            continue
        if not rows:
            continue
        results.append(import_rows(coop_slug, key, rows, mode=mode))
    return results
