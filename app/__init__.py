import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from app.config import (
    CDA_REPORT_FORMS,
    COOP_GREEN,
    COOP_GREEN_DARK,
    COOP_GREEN_LIGHT,
    COOP_GOLD,
    SECRET_KEY,
    USER_ROLES,
    assignable_user_roles,
    build_database_uri,
    can_manage_coops,
    can_post_entries,
    database_config_error,
    is_admin_role,
    is_platform_admin_role,
    is_platform_admin_session,
    is_serverless_host,
    sqlalchemy_engine_options,
)
from app.bir_cas_config import BIR_CAS_REQUIREMENTS, SYSTEM_NAME, SYSTEM_VERSION
from app.modules_config import APP_MODULES, nav_modules

db = SQLAlchemy()
log = logging.getLogger(__name__)

from app.platform_models import CoopModuleSubscription, CoopRegistry  # noqa: F401, E402
from app.tenant_manager import coop_logo_url, get_coop_registry, subscribed_module_keys  # noqa: F401, E402
import app.models  # noqa: F401, E402


def create_app():
    base = Path(__file__).parent
    template_folder = str((base.parent / "templates").resolve())
    static_folder = str((base.parent / "static").resolve())

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = SECRET_KEY
    CORS(app)

    load_dotenv(base.parent / ".env")

    db_uri = build_database_uri()
    db_error = database_config_error()
    if db_error:
        log.error(db_error)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = sqlalchemy_engine_options()
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    db.init_app(app)

    @app.context_processor
    def inject_globals():
        from flask import session

        registry = None
        modules = []
        try:
            registry = get_coop_registry()
            if registry:
                modules = subscribed_module_keys(registry.id)
        except Exception:
            pass
        current_role = session.get("role")
        return {
            "coop_green": COOP_GREEN,
            "coop_green_dark": COOP_GREEN_DARK,
            "coop_green_light": COOP_GREEN_LIGHT,
            "coop_gold": COOP_GOLD,
            "user_roles": assignable_user_roles(current_role),
            "can_post_entries": can_post_entries,
            "is_admin_role": is_admin_role,
            "is_platform_admin_role": is_platform_admin_role,
            "is_platform_admin": is_platform_admin_session(session),
            "can_manage_coops": can_manage_coops(session),
            "cda_report_forms": CDA_REPORT_FORMS,
            "bir_cas_requirements": BIR_CAS_REQUIREMENTS,
            "system_name": SYSTEM_NAME,
            "system_version": SYSTEM_VERSION,
            "app_modules": APP_MODULES,
            "subscribed_modules": set(modules),
            "nav_module_items": nav_modules(modules),
            "coop_registry": registry,
            "coop_logo_url": coop_logo_url(registry),
            "db_config_error": database_config_error(),
        }

    @app.route("/favicon.ico")
    @app.route("/favicon.png")
    def favicon():
        return send_from_directory(
            os.path.join(app.static_folder, "images"),
            "coop_logo.svg",
            mimetype="image/svg+xml",
        )

    from app.routes import main_routes

    app.register_blueprint(main_routes)

    with app.app_context():
        _bootstrap_database()

    log_handler = logging.getLogger("werkzeug")
    log_handler.setLevel(logging.WARNING)

    return app


def _bootstrap_database():
    """Initialize schema, cooperative registry, and default users."""
    from werkzeug.security import generate_password_hash

    from app.models import User
    from app.tenant_provisioning import migrate_legacy_single_tenant

    try:
        db.create_all()
        _ensure_schema_updates()
        migrate_legacy_single_tenant()

        if not is_serverless_host():
            _write_static_migration_templates()

        from app.services import seed_tenant_database
        seed_tenant_database()

        if User.query.filter_by(username="PlatformAdmin").first() is None:
            db.session.add(User(
                username="PlatformAdmin",
                full_name="Platform Administrator",
                email="platform@coopbooks.local",
                role="PlatformAdmin",
                status="Active",
                password_hash=generate_password_hash("platform123"),
            ))
            db.session.commit()
    except Exception as exc:
        log.error("Database bootstrap failed: %s", exc)
        if is_serverless_host() and not os.getenv("DATABASE_URL") and not os.getenv("DB_IP"):
            log.error(
                "Set DATABASE_URL to your hosted Postgres connection string in environment variables."
            )


def _write_static_migration_templates():
    from app.migration_config import IMPORT_ORDER
    from app.migration_service import build_all_templates_zip, build_template_workbook

    out_dir = Path(__file__).parent.parent / "static" / "migration_templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in IMPORT_ORDER:
        buf = build_template_workbook(spec["key"])
        (out_dir / spec["filename"]).write_bytes(buf.getvalue())
    (out_dir / "coopbooks-migration-templates.zip").write_bytes(build_all_templates_zip().getvalue())


def _ensure_schema_updates():
    from sqlalchemy import text

    from app.models import User

    statements = [
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS email VARCHAR(120)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS address VARCHAR(255)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS last_name VARCHAR(80)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS first_name VARCHAR(80)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS middle_name VARCHAR(80)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS tin VARCHAR(30)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS bod_acceptance_resolution VARCHAR(50)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS membership_type VARCHAR(30) DEFAULT 'Regular'",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS initial_shares NUMERIC(12, 2) DEFAULT 0",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS initial_subscription_amount NUMERIC(14, 2) DEFAULT 0",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS initial_paid_up_capital NUMERIC(14, 2) DEFAULT 0",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_date DATE",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS gender VARCHAR(20)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS civil_status VARCHAR(30)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS highest_education VARCHAR(40)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS occupation_income_source VARCHAR(120)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS number_of_dependents INTEGER DEFAULT 0",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS religion_social_affiliation VARCHAR(120)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS annual_income NUMERIC(14, 2)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS register_entry_date DATE",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS termination_date DATE",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS termination_bod_resolution VARCHAR(50)",
        "ALTER TABLE members ALTER COLUMN full_name TYPE VARCHAR(200)",
        "ALTER TABLE cooperatives ADD COLUMN IF NOT EXISTS tin VARCHAR(30)",
        "ALTER TABLE cooperatives ADD COLUMN IF NOT EXISTS rdo VARCHAR(80)",
        "ALTER TABLE coop_registry ADD COLUMN IF NOT EXISTS logo_data BYTEA",
        "ALTER TABLE coop_registry ADD COLUMN IF NOT EXISTS logo_mime_type VARCHAR(80)",
        "CREATE INDEX IF NOT EXISTS ix_journal_entries_entry_date ON journal_entries (entry_date)",
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_account_id ON journal_lines (account_id)",
        "CREATE INDEX IF NOT EXISTS ix_journal_lines_entry_id ON journal_lines (entry_id)",
    ]
    with db.engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    from app.models import Member

    changed = False
    for member in Member.query.all():
        if not member.last_name and not member.first_name and member.full_name:
            member.first_name = member.full_name
            member.last_name = member.last_name or ""
            changed = True
        if not member.register_entry_date and member.created_at:
            member.register_entry_date = member.created_at.date()
            changed = True
        if not member.membership_type:
            member.membership_type = "Regular"
            changed = True
    if changed:
        db.session.commit()

    from app.config import normalize_role

    changed = False
    for user in User.query.all():
        normalized = normalize_role(user.role)
        if user.role != normalized:
            user.role = normalized
            changed = True
    if changed:
        db.session.commit()


def _ensure_member_columns():
    _ensure_schema_updates()


def _ensure_coop_columns():
    pass


def _migrate_user_roles():
    pass
