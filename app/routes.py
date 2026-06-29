import traceback
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, jsonify, make_response, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from app import db
from app.accounting_service import (
    accounts_with_balances,
    dashboard_columnar,
    dashboard_stats,
    dashboard_trends,
    general_journal_book,
    general_ledger_accounts,
    member_subsidiary_ledger,
    recent_journal_entries,
    statement_of_financial_condition,
    statement_of_operations,
    trial_balance,
)
from app.audit_service import audit_trail_rows, log_audit
from app.auth import platform_admin_required, register_route_guards
from app.bir_cas_config import BIR_CAS_REQUIREMENTS
from app.bir_cas_service import context_for_slug, documentation_index_context
from app.config import USER_ROLES, can_post_entries, normalize_role, safe_login_redirect
from app.migration_config import IMPORT_ORDER, MIGRATION_TABLES
from app.migration_service import (
    build_all_templates_zip,
    build_template_workbook,
    import_batch,
    read_upload_rows,
    validate_import,
)
from app.modules_config import APP_MODULES
from app.platform_models import CoopModuleSubscription, CoopRegistry, PlatformUser
from app.tenant_manager import (
    coop_upload_dir,
    get_current_coop,
    list_active_coops,
    normalize_slug,
    switch_tenant_bind,
)
from app.tenant_provisioning import provision_coop
from app.member_service import (
    MEMBER_STATUSES,
    POSTABLE_TXN_TYPES,
    TXN_TYPE_LABELS,
    create_opening_ledger_entries,
    display_txn_type,
    member_ledger_history,
    member_ledger_summary,
    member_totals,
    next_member_no,
    parse_ledger_form,
    parse_member_form,
    record_ledger_entry,
)
from app.models import Account, Cooperative, JournalEntry, JournalLine, Member, MemberLedger, User, local_time
from app.pdf_service import (
    BIR_BOOK_TYPES,
    bir_book_pdf_filename,
    render_book_pdf,
    render_cas_document_pdf,
)
from app.user_manual import user_manual_context
from app.user_service import apply_user_update, list_users, parse_user_form

main_routes = Blueprint("main_routes", __name__)
register_route_guards(main_routes)


@main_routes.route("/")
def index():
    coops = list_active_coops()
    return render_template("index.html", coops=coops)


@main_routes.route("/api/coops")
def api_coop_list():
    coops = list_active_coops()
    return jsonify([
        {"slug": c.slug, "name": c.name}
        for c in coops
    ])


@main_routes.route("/uploads/coops/<slug>/<filename>")
def coop_logo(slug, filename):
    directory = coop_upload_dir(slug)
    return send_from_directory(directory, filename)


@main_routes.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main_routes.index"))


@main_routes.route("/login", methods=["GET", "POST"])
def login():
    try:
        next_param = request.args.get("next", "")
        coops = list_active_coops()

        if request.method == "POST":
            data = request.get_json() if request.is_json else request.form
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            coop_code = normalize_slug(data.get("coop_code", ""))
            is_platform = data.get("platform_admin") in (True, "true", "1", "on", "yes")
            next_param = data.get("next", next_param)

            if is_platform or coop_code == "platform":
                platform_user = PlatformUser.query.filter_by(username=username).first()
                if platform_user and platform_user.check_password(password):
                    if (platform_user.status or "Active") != "Active":
                        message = "Platform account is inactive."
                        if request.is_json:
                            return jsonify({"success": False, "message": message})
                        flash(message, "danger")
                        return render_template("login.html", next_url=next_param, coops=coops)

                    session.clear()
                    session["is_platform_admin"] = True
                    session["user_id"] = platform_user.id
                    session["username"] = platform_user.username
                    session["fullname"] = platform_user.full_name
                    session["role"] = "PlatformAdmin"
                    redirect_to = url_for("main_routes.admin_coops")
                    if request.is_json:
                        return jsonify({"success": True, "redirect": redirect_to})
                    flash("Platform login successful", "success")
                    return redirect(redirect_to)

            registry = CoopRegistry.query.filter_by(slug=coop_code, status="Active").first()
            if not registry:
                message = "Invalid or inactive cooperative code."
                if request.is_json:
                    return jsonify({"success": False, "message": message})
                flash(message, "danger")
                return render_template("login.html", next_url=next_param, coops=coops)

            switch_tenant_bind(registry.slug)
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                if (user.status or "Active") != "Active":
                    message = "Account is inactive. Contact an administrator."
                    if request.is_json:
                        return jsonify({"success": False, "message": message})
                    flash(message, "danger")
                    return render_template("login.html", next_url=next_param, coops=coops)

                session.clear()
                session["coop_slug"] = registry.slug
                session["coop_name"] = registry.name
                session["user_id"] = user.user_id
                session["username"] = user.username
                session["fullname"] = user.full_name
                session["role"] = normalize_role(user.role)
                session["is_platform_admin"] = False

                redirect_to = safe_login_redirect(next_param)
                if request.is_json:
                    return jsonify({"success": True, "redirect": redirect_to})
                flash("Login successful", "success")
                return redirect(redirect_to)

            message = "Invalid credentials"
            if request.is_json:
                return jsonify({"success": False, "message": message})
            flash(message, "danger")

        return render_template("login.html", next_url=next_param, coops=coops)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500


@main_routes.route("/dashboard")
def dashboard():
    coop = get_current_coop()
    role = normalize_role(session.get("role"))
    return render_template(
        "dash.html",
        fullname=session.get("fullname") or "Guest",
        role=role,
        coop=coop,
        can_post=can_post_entries(role),
    )


@main_routes.route("/api/dashboard_stats")
def api_dashboard_stats():
    return jsonify(dashboard_stats())


@main_routes.route("/api/dashboard_trends")
def api_dashboard_trends():
    months = request.args.get("months", 6, type=int)
    months = max(3, min(months, 12))
    return jsonify(dashboard_trends(months=months))


@main_routes.route("/api/dashboard_columnar")
def api_dashboard_columnar():
    return jsonify(dashboard_columnar())


@main_routes.route("/api/recent_journals")
def api_recent_journals():
    return jsonify(recent_journal_entries())


@main_routes.route("/accounts")
def accounts():
    category = request.args.get("category", "").strip()
    code = request.args.get("code", "").strip()
    account_type = request.args.get("type", "").strip()

    filters = {}
    if category:
        filters["category"] = category
    if code:
        filters["code"] = code
    if account_type:
        filters["account_type"] = account_type

    rows = accounts_with_balances(filters or None)
    page_title = "Chart of Accounts"
    if category:
        page_title = category
    elif code:
        acct = Account.query.filter_by(code=code).first()
        page_title = acct.name if acct else f"Account {code}"

    return render_template(
        "accounts.html",
        account_rows=rows,
        filter_category=category,
        filter_code=code,
        page_heading=page_title,
    )


@main_routes.route("/members")
def members():
    focus = request.args.get("focus", "").strip().lower()
    members_list = Member.query.order_by(Member.member_no).all()
    focus_labels = {
        "share": "Share Capital",
        "savings": "Savings Deposits",
    }
    totals = member_totals(members_list)
    role = normalize_role(session.get("role"))
    ledger_summaries = {m.id: member_ledger_summary(m.id) for m in members_list}
    recent_ledger = {m.id: member_ledger_history(m.id)[:5] for m in members_list}
    return render_template(
        "members.html",
        members=members_list,
        focus=focus if focus in focus_labels else "",
        focus_label=focus_labels.get(focus, ""),
        totals=totals,
        can_add=can_post_entries(role),
        member_statuses=MEMBER_STATUSES,
        next_member_no=next_member_no(),
        default_date=local_time().date().isoformat(),
        ledger_summaries=ledger_summaries,
        recent_ledger=recent_ledger,
        display_txn_type=display_txn_type,
    )


@main_routes.route("/members/add", methods=["POST"])
def members_add():
    parsed, error = parse_member_form(request.form)
    if error:
        flash(error, "danger")
        return redirect(url_for("main_routes.members"))

    member = Member(**parsed)
    db.session.add(member)
    db.session.flush()
    create_opening_ledger_entries(
        member,
        posted_by=session.get("fullname", session.get("username", "System")),
        share_amount=parsed["share_capital"],
        savings_amount=parsed["savings_balance"],
    )
    db.session.commit()
    log_audit("CREATE", "Member", member.id, f"{member.member_no} — {member.full_name}")
    flash(f"Member {member.member_no} — {member.full_name} added successfully.", "success")
    return redirect(url_for("main_routes.members"))


@main_routes.route("/members/<member_no>/ledger")
def member_ledger(member_no):
    member = Member.query.filter_by(member_no=member_no).first_or_404()
    role = normalize_role(session.get("role"))
    history = member_ledger_history(member.id)
    summary = member_ledger_summary(member.id)
    return render_template(
        "member_ledger.html",
        member=member,
        history=history,
        summary=summary,
        can_post=can_post_entries(role),
        txn_types=POSTABLE_TXN_TYPES,
        txn_type_labels=TXN_TYPE_LABELS,
        display_txn_type=display_txn_type,
        default_date=local_time().date().isoformat(),
    )


@main_routes.route("/members/<member_no>/ledger/add", methods=["POST"])
def member_ledger_add(member_no):
    member = Member.query.filter_by(member_no=member_no).first_or_404()
    parsed, error = parse_ledger_form(request.form, member)
    if error:
        flash(error, "danger")
        return redirect(url_for("main_routes.member_ledger", member_no=member_no))

    record_ledger_entry(
        member,
        parsed["txn_date"],
        parsed["txn_type"],
        parsed["amount"],
        reference=parsed["reference"],
        description=parsed["description"],
        posted_by=session.get("fullname", session.get("username")),
        is_debit=parsed["is_debit"],
    )
    db.session.commit()
    log_audit(
        "CREATE", "MemberLedger", member.id,
        f"{member.member_no} — {parsed['txn_type']}",
        {"amount": str(parsed["amount"]), "type": parsed["txn_type"]},
    )
    flash("Transaction recorded in member ledger.", "success")
    return redirect(url_for("main_routes.member_ledger", member_no=member_no))


@main_routes.route("/api/members/<member_no>/ledger")
def api_member_ledger(member_no):
    member = Member.query.filter_by(member_no=member_no).first_or_404()
    return jsonify({
        "summary": member_ledger_summary(member.id),
        "history": member_ledger_history(member.id),
    })


@main_routes.route("/api/members/next_no")
def api_next_member_no():
    return jsonify({"member_no": next_member_no()})


@main_routes.route("/journal")
def journal_list():
    entries = JournalEntry.query.order_by(JournalEntry.entry_date.desc()).all()
    return render_template(
        "journal_list.html",
        entries=entries,
        can_post=can_post_entries(session.get("role")),
    )


@main_routes.route("/journal/new", methods=["GET", "POST"])
def journal_new():
    accounts_list = Account.query.filter_by(is_active=True).order_by(Account.code).all()

    if request.method == "POST":
        try:
            entry_date = request.form.get("entry_date")
            description = request.form.get("description", "").strip()
            reference = request.form.get("reference", "").strip()
            entry_no = request.form.get("entry_no", "").strip()

            account_ids = request.form.getlist("account_id")
            debits = request.form.getlist("debit")
            credits = request.form.getlist("credit")
            memos = request.form.getlist("memo")

            if not entry_no:
                entry_no = _next_entry_no()

            if JournalEntry.query.filter_by(entry_no=entry_no).first():
                flash("Entry number already exists.", "danger")
                return redirect(url_for("main_routes.journal_new"))

            total_debit = Decimal("0")
            total_credit = Decimal("0")
            lines_data = []

            for i, account_id in enumerate(account_ids):
                if not account_id:
                    continue
                try:
                    debit = Decimal(debits[i] or "0")
                    credit = Decimal(credits[i] or "0")
                except (InvalidOperation, IndexError):
                    continue
                if debit == 0 and credit == 0:
                    continue
                total_debit += debit
                total_credit += credit
                memo = memos[i] if i < len(memos) else ""
                lines_data.append((account_id, debit, credit, memo))

            if not lines_data:
                flash("Add at least one journal line.", "danger")
                return redirect(url_for("main_routes.journal_new"))

            if total_debit != total_credit:
                flash(f"Debits ({total_debit}) must equal credits ({total_credit}).", "danger")
                return redirect(url_for("main_routes.journal_new"))

            entry = JournalEntry(
                entry_no=entry_no,
                entry_date=entry_date,
                description=description,
                reference=reference,
                posted_by=session.get("fullname", session.get("username")),
            )
            db.session.add(entry)
            db.session.flush()

            for account_id, debit, credit, memo in lines_data:
                db.session.add(JournalLine(
                    entry_id=entry.id,
                    account_id=int(account_id),
                    debit=debit,
                    credit=credit,
                    memo=memo,
                ))

            db.session.commit()
            log_audit(
                "CREATE", "JournalEntry", entry.id, entry.entry_no,
                {"description": description, "total": str(total_debit)},
            )
            flash(f"Journal entry {entry_no} posted successfully.", "success")
            return redirect(url_for("main_routes.journal_list"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error posting entry: {e}", "danger")

    return render_template(
        "journal_form.html",
        accounts=accounts_list,
        default_date=local_time().date().isoformat(),
        next_entry_no=_next_entry_no(),
    )


@main_routes.route("/journal/<entry_no>")
def journal_detail(entry_no):
    entry = JournalEntry.query.filter_by(entry_no=entry_no).first_or_404()
    return render_template("journal_detail.html", entry=entry)


@main_routes.route("/reports")
def reports():
    return redirect(url_for("main_routes.reports_cda"))


@main_routes.route("/reports/cda")
def reports_cda():
    return render_template("reports_cda.html")


@main_routes.route("/reports/bir-books")
def reports_bir_books():
    return render_template("reports_bir_books.html")


@main_routes.route("/reports/sfc")
def report_sfc():
    coop = get_current_coop()
    data = statement_of_financial_condition()
    return render_template("report_sfc.html", coop=coop, report=data, as_of=local_time().date())


@main_routes.route("/reports/operations")
def report_operations():
    coop = get_current_coop()
    data = statement_of_operations()
    return render_template("report_operations.html", coop=coop, report=data, as_of=local_time().date())


@main_routes.route("/reports/trial-balance")
def report_trial_balance():
    coop = get_current_coop()
    rows = trial_balance()
    total_debit = sum(r["debit"] for r in rows)
    total_credit = sum(r["credit"] for r in rows)
    return render_template(
        "report_trial_balance.html",
        coop=coop,
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        as_of=local_time().date(),
    )


@main_routes.route("/reports/general-journal")
def report_general_journal():
    coop = get_current_coop()
    entries = general_journal_book()
    return render_template(
        "report_general_journal.html",
        coop=coop,
        entries=entries,
        as_of=local_time().date(),
    )


@main_routes.route("/reports/general-ledger")
def report_general_ledger():
    coop = get_current_coop()
    account_code = request.args.get("code", "").strip()
    accounts = general_ledger_accounts(account_code or None)
    return render_template(
        "report_general_ledger.html",
        coop=coop,
        accounts=accounts,
        filter_code=account_code,
        as_of=local_time().date(),
    )


@main_routes.route("/reports/member-subsidiary")
def report_member_subsidiary():
    coop = get_current_coop()
    ledgers = member_subsidiary_ledger()
    return render_template(
        "report_member_subsidiary.html",
        coop=coop,
        ledgers=ledgers,
        as_of=local_time().date(),
    )


@main_routes.route("/documentation")
def documentation_index():
    ctx = documentation_index_context()
    ctx["doc_slug"] = ""
    return render_template("documentation/index.html", **ctx)


@main_routes.route("/documentation/audit-trail")
def documentation_audit_trail():
    rows = audit_trail_rows(limit=500)
    return render_template(
        "documentation/audit_trail.html",
        rows=rows,
        requirement={"title": "Audit Trail", "bir_reference": "Annex A CDR Item 4 / Annex B Item 8"},
    )


def _bir_book_pdf_response(book_type):
    if book_type not in BIR_BOOK_TYPES:
        return None
    buffer = render_book_pdf(book_type)
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{bir_book_pdf_filename(book_type)}"'
    )
    return response


@main_routes.route("/reports/bir-books/<book_type>/pdf")
def report_bir_book_pdf(book_type):
    response = _bir_book_pdf_response(book_type)
    if response is None:
        flash("Invalid book type.", "warning")
        return redirect(url_for("main_routes.reports_bir_books"))
    return response


@main_routes.route("/documentation/books/<book_type>/pdf")
def documentation_book_pdf(book_type):
    response = _bir_book_pdf_response(book_type)
    if response is None:
        flash("Invalid book type.", "warning")
        return redirect(url_for("main_routes.documentation_index"))
    return response


@main_routes.route("/documentation/<slug>")
def documentation_view(slug):
    if slug not in {r["slug"] for r in BIR_CAS_REQUIREMENTS}:
        flash("Documentation section not found.", "warning")
        return redirect(url_for("main_routes.documentation_index"))
    ctx = context_for_slug(slug)
    if not ctx:
        flash("Documentation section not found.", "warning")
        return redirect(url_for("main_routes.documentation_index"))
    ctx["doc_slug"] = slug
    return render_template(f"documentation/{slug}.html", **ctx)


@main_routes.route("/documentation/<slug>/pdf")
def documentation_pdf(slug):
    if slug not in {r["slug"] for r in BIR_CAS_REQUIREMENTS}:
        flash("Documentation section not found.", "warning")
        return redirect(url_for("main_routes.documentation_index"))
    buffer = render_cas_document_pdf(slug)
    if not buffer:
        flash("Unable to generate PDF.", "danger")
        return redirect(url_for("main_routes.documentation_view", slug=slug))
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=bir-cas-{slug}.pdf"
    return response


@main_routes.route("/about/user-manual")
def about_user_manual():
    ctx = user_manual_context()
    return render_template("about/user_manual.html", **ctx)


@main_routes.route("/admin/coops")
@platform_admin_required
def admin_coops():
    coops = CoopRegistry.query.order_by(CoopRegistry.name).all()
    module_map = {}
    for coop in coops:
        module_map[coop.id] = {
            m.module_key: m.is_active for m in coop.modules
        }
    return render_template(
        "admin/coops.html",
        coops=coops,
        app_modules=APP_MODULES,
        module_map=module_map,
    )


@main_routes.route("/admin/coops/register", methods=["GET", "POST"])
@platform_admin_required
def admin_coops_register():
    if request.method == "POST":
        form = request.form.to_dict(flat=False)
        data = {k: (v[0] if isinstance(v, list) else v) for k, v in form.items()}
        data["modules"] = request.form.getlist("modules")
        data["seed_samples"] = "seed_samples" in request.form
        registry, error = provision_coop(data)
        if error and not registry:
            flash(error, "danger")
        elif error:
            flash(f"Coop registered with warnings: {error}", "warning")
            return redirect(url_for("main_routes.admin_coop_detail", slug=registry.slug))
        else:
            flash(f"Cooperative '{registry.name}' registered successfully.", "success")
            return redirect(url_for("main_routes.admin_coop_detail", slug=registry.slug))

    return render_template("admin/coop_register.html", app_modules=APP_MODULES)


@main_routes.route("/admin/migration")
@platform_admin_required
def admin_migration():
    coops = CoopRegistry.query.order_by(CoopRegistry.name).all()
    return render_template(
        "admin/migration.html",
        coops=coops,
        migration_tables=IMPORT_ORDER,
    )


@main_routes.route("/admin/migration/templates/<table_key>.xlsx")
@platform_admin_required
def admin_migration_template(table_key):
    if table_key not in {t["key"] for t in MIGRATION_TABLES}:
        flash("Unknown template.", "warning")
        return redirect(url_for("main_routes.admin_migration"))
    spec = next(t for t in MIGRATION_TABLES if t["key"] == table_key)
    buffer = build_template_workbook(table_key)
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={spec['filename']}"
    return response


@main_routes.route("/admin/migration/templates/all.zip")
@platform_admin_required
def admin_migration_templates_zip():
    buffer = build_all_templates_zip()
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/zip"
    response.headers["Content-Disposition"] = "attachment; filename=coopbooks-migration-templates.zip"
    return response


@main_routes.route("/admin/migration/preview", methods=["POST"])
@platform_admin_required
def admin_migration_preview():
    coop_slug = normalize_slug(request.form.get("coop_slug", ""))
    registry = CoopRegistry.query.filter_by(slug=coop_slug).first()
    if not registry:
        return jsonify({"status": "error", "msg": "Invalid cooperative code."}), 400

    previews = []
    for spec in IMPORT_ORDER:
        file = request.files.get(spec["key"])
        if not file or not file.filename:
            continue
        rows, errors = read_upload_rows(file, spec["key"])
        fk_warnings = []
        if rows and not errors:
            val = validate_import(coop_slug, spec["key"], rows)
            fk_warnings = val.get("errors", [])
        previews.append({
            "key": spec["key"],
            "label": spec["label"],
            "filename": file.filename,
            "row_count": len(rows),
            "errors": errors,
            "warnings": fk_warnings,
            "sample": [{k: v for k, v in r.items() if k != "_row"} for r in rows[:3]] if rows else [],
        })

    if not previews:
        return jsonify({"status": "error", "msg": "No files selected for preview."}), 400

    return jsonify({"status": "success", "previews": previews})


@main_routes.route("/admin/migration/import", methods=["POST"])
@platform_admin_required
def admin_migration_import():
    coop_slug = normalize_slug(request.form.get("coop_slug", ""))
    registry = CoopRegistry.query.filter_by(slug=coop_slug).first()
    if not registry:
        flash("Invalid cooperative code.", "danger")
        return redirect(url_for("main_routes.admin_migration"))

    mode = request.form.get("import_mode", "append")
    if mode not in ("append", "replace"):
        mode = "append"

    uploads = {}
    for spec in IMPORT_ORDER:
        file = request.files.get(spec["key"])
        if file and file.filename:
            uploads[spec["key"]] = file

    if not uploads:
        flash("Select at least one Excel file to import.", "warning")
        return redirect(url_for("main_routes.admin_migration"))

    results = import_batch(coop_slug, uploads, mode=mode)
    total_imported = sum(r.get("imported", 0) for r in results)
    total_errors = sum(len(r.get("errors", [])) for r in results)

    return render_template(
        "admin/migration.html",
        coops=CoopRegistry.query.order_by(CoopRegistry.name).all(),
        migration_tables=IMPORT_ORDER,
        import_results=results,
        selected_coop=coop_slug,
        import_mode=mode,
        total_imported=total_imported,
        total_errors=total_errors,
    )


@main_routes.route("/admin/coops/<slug>", methods=["GET", "POST"])
@platform_admin_required
def admin_coop_detail(slug):
    coop = CoopRegistry.query.filter_by(slug=slug).first_or_404()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_profile":
            coop.name = request.form.get("name", coop.name).strip()
            coop.status = request.form.get("status", coop.status)
            coop.registration_no = request.form.get("registration_no", "").strip() or None
            coop.tin = request.form.get("tin", "").strip() or None
            coop.rdo = request.form.get("rdo", "").strip() or None
            coop.coop_type = request.form.get("coop_type", "").strip() or None
            coop.address = request.form.get("address", "").strip() or None
            coop.contact_email = request.form.get("contact_email", "").strip() or None
            db.session.commit()
            flash("Cooperative profile updated.", "success")
        elif action == "update_modules":
            selected = set(request.form.getlist("modules"))
            for sub in coop.modules:
                sub.is_active = sub.module_key in selected
            db.session.commit()
            flash("Module subscriptions updated.", "success")
        elif action == "upload_logo":
            file = request.files.get("logo")
            if file and file.filename:
                ext = secure_filename(file.filename).rsplit(".", 1)[-1].lower()
                if ext not in ("png", "jpg", "jpeg", "svg", "webp", "gif"):
                    flash("Logo must be PNG, JPG, SVG, or WebP.", "danger")
                else:
                    filename = f"logo.{ext}"
                    path = coop_upload_dir(slug)
                    file.save(path / filename)
                    coop.logo_filename = filename
                    db.session.commit()
                    flash("Logo uploaded.", "success")
        return redirect(url_for("main_routes.admin_coop_detail", slug=slug))

    active_modules = {m.module_key for m in coop.modules if m.is_active}
    return render_template(
        "admin/coop_detail.html",
        coop=coop,
        app_modules=APP_MODULES,
        active_modules=active_modules,
    )


@main_routes.route("/admin/users")
def admin_users():
    users = list_users()
    return render_template(
        "users.html",
        users=users,
        user_roles=USER_ROLES,
        current_user_id=session.get("user_id"),
    )


@main_routes.route("/admin/users/add", methods=["POST"])
def admin_users_add():
    parsed, error = parse_user_form(request.form, require_password=True)
    if error:
        return jsonify({"status": "error", "msg": error}), 400

    user = User(**{k: v for k, v in parsed.items() if k != "password_hash"})
    user.password_hash = parsed["password_hash"]
    db.session.add(user)
    db.session.commit()
    log_audit("CREATE", "User", user.user_id, user.username, {"role": user.role})
    return jsonify({"status": "success", "msg": f"User '{user.username}' added successfully."})


@main_routes.route("/admin/users/<int:user_id>/update", methods=["POST"])
def admin_users_update(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "msg": "User not found."}), 404

    parsed, error = parse_user_form(request.form, user_id=user_id, require_password=False)
    if error:
        return jsonify({"status": "error", "msg": error}), 400

    apply_user_update(user, parsed)
    db.session.commit()
    log_audit("UPDATE", "User", user.user_id, user.username, {"role": user.role})
    return jsonify({"status": "success", "msg": f"User '{user.username}' updated successfully."})


@main_routes.route("/admin/users/<int:user_id>/delete", methods=["DELETE"])
def admin_users_delete(user_id):
    if user_id == session.get("user_id"):
        return jsonify({"status": "error", "msg": "You cannot delete your own account."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "msg": "User not found."}), 404

    if User.query.count() <= 1:
        return jsonify({"status": "error", "msg": "At least one user must remain."}), 400

    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_audit("DELETE", "User", user_id, username)
    return jsonify({"status": "success", "msg": f"User '{username}' deleted successfully."})


def _next_entry_no():
    year = local_time().year
    prefix = f"JE-{year}-"
    latest = (
        JournalEntry.query
        .filter(JournalEntry.entry_no.like(f"{prefix}%"))
        .order_by(JournalEntry.entry_no.desc())
        .first()
    )
    if not latest:
        return f"{prefix}001"
    try:
        seq = int(latest.entry_no.split("-")[-1]) + 1
    except ValueError:
        seq = 1
    return f"{prefix}{seq:03d}"
