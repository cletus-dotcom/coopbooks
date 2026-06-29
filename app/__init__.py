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
    DB_CONFIG,
    SECRET_KEY,
    USER_ROLES,
    build_database_uri,
    can_manage_coops,
    can_post_entries,
    is_admin_role,
    is_platform_admin_session,
)
from app.bir_cas_config import BIR_CAS_REQUIREMENTS, SYSTEM_NAME, SYSTEM_VERSION
from app.modules_config import APP_MODULES, nav_modules

db = SQLAlchemy()
log = logging.getLogger(__name__)

from app.platform_models import CoopModuleSubscription, CoopRegistry, PlatformUser  # noqa: F401, E402
from app.tenant_manager import TENANT_BIND, coop_logo_url, get_registry_from_session, subscribed_module_keys  # noqa: E402
import app.models  # noqa: F401, E402 — register tenant models


def create_app():
    base = Path(__file__).parent
    template_folder = str((base.parent / "templates").resolve())
    static_folder = str((base.parent / "static").resolve())

    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.secret_key = SECRET_KEY
    CORS(app)

    load_dotenv(base.parent / ".env")

    platform_uri = build_database_uri(DB_CONFIG["platform_db_name"])
    tenant_uri = build_database_uri(DB_CONFIG["db_name"])

    app.config["SQLALCHEMY_DATABASE_URI"] = platform_uri
    app.config["SQLALCHEMY_BINDS"] = {TENANT_BIND: tenant_uri}
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    db.init_app(app)

    @app.context_processor
    def inject_globals():
        from flask import session

        registry = get_registry_from_session()
        modules = subscribed_module_keys(registry.id if registry else None) if session.get("coop_slug") else []
        return {
            "coop_green": COOP_GREEN,
            "coop_green_dark": COOP_GREEN_DARK,
            "coop_green_light": COOP_GREEN_LIGHT,
            "coop_gold": COOP_GOLD,
            "user_roles": USER_ROLES,
            "can_post_entries": can_post_entries,
            "is_admin_role": is_admin_role,
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
        }

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "static", "images"),
            "coop_logo.svg",
            mimetype="image/svg+xml",
        )

    from app.routes import main_routes

    app.register_blueprint(main_routes)

    with app.app_context():
        _bootstrap_databases()

    log_handler = logging.getLogger("werkzeug")
    log_handler.setLevel(logging.WARNING)

    return app


def _bootstrap_databases():
    """Initialize platform registry and default tenant."""
    from sqlalchemy import create_engine, text

    from app.platform_models import PlatformUser
    from app.tenant_provisioning import migrate_legacy_single_tenant
    from app.tenant_manager import switch_tenant_bind
    from werkzeug.security import generate_password_hash

    _ensure_platform_database_exists()

    db.create_all()
    migrate_legacy_single_tenant()
    _write_static_migration_templates()

    if PlatformUser.query.filter_by(username="PlatformAdmin").first() is None:
        admin = PlatformUser(
            username="PlatformAdmin",
            full_name="Platform Administrator",
            email="platform@coopbooks.local",
            status="Active",
            password_hash=generate_password_hash("platform123"),
        )
        db.session.add(admin)
        db.session.commit()

    try:
        switch_tenant_bind("demo")
        db.create_all()
        _ensure_tenant_columns()
        from app.services import seed_tenant_database
        seed_tenant_database()
    except Exception as exc:
        log.warning("Tenant bootstrap skipped: %s", exc)


def _write_static_migration_templates():
    """Write Excel import templates to static/migration_templates/."""
    from app.migration_config import IMPORT_ORDER
    from app.migration_service import build_all_templates_zip, build_template_workbook

    out_dir = Path(__file__).parent.parent / "static" / "migration_templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in IMPORT_ORDER:
        buf = build_template_workbook(spec["key"])
        (out_dir / spec["filename"]).write_bytes(buf.getvalue())
    (out_dir / "coopbooks-migration-templates.zip").write_bytes(build_all_templates_zip().getvalue())


def _ensure_platform_database_exists():
    from sqlalchemy import create_engine, text

    db_name = DB_CONFIG["platform_db_name"]
    admin_uri = build_database_uri("postgres")
    try:
        engine = create_engine(admin_uri, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        engine.dispose()
    except Exception as exc:
        log.warning("Platform database auto-create skipped: %s", exc)


def _ensure_tenant_columns():
    from sqlalchemy import text

    statements = [
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS email VARCHAR(120)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS address VARCHAR(255)",
        "ALTER TABLE cooperatives ADD COLUMN IF NOT EXISTS tin VARCHAR(30)",
        "ALTER TABLE cooperatives ADD COLUMN IF NOT EXISTS rdo VARCHAR(80)",
    ]
    for stmt in statements:
        engine = db.engines.get(TENANT_BIND)
        if engine:
            with engine.begin() as conn:
                conn.execute(text(stmt))

    from app.config import normalize_role
    from app.models import User

    changed = False
    for user in User.query.all():
        normalized = normalize_role(user.role)
        if user.role != normalized:
            user.role = normalized
            changed = True
    if changed:
        db.session.commit()


def _ensure_member_columns():
    _ensure_tenant_columns()


def _ensure_coop_columns():
    pass


def _migrate_user_roles():
    pass
