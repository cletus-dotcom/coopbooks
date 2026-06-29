"""Provision a new cooperative tenant database."""

import logging

from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

from app.config import DB_CONFIG, build_database_uri
from app.modules_config import APP_MODULES
from app.platform_models import CoopModuleSubscription, CoopRegistry
from app.tenant_manager import db_name_for_slug, ensure_default_modules, is_valid_slug, normalize_slug

log = logging.getLogger(__name__)


def provision_coop(form_data):
    """Create registry entry, database, schema, and initial admin user."""
    from app import db

    slug = normalize_slug(form_data.get("slug", ""))
    name = (form_data.get("name") or "").strip()
    if not is_valid_slug(slug):
        return None, "Coop code must be 3–40 characters (lowercase letters, numbers, hyphens)."
    if not name:
        return None, "Cooperative name is required."
    if CoopRegistry.query.filter_by(slug=slug).first():
        return None, f"Coop code '{slug}' is already registered."

    db_name = db_name_for_slug(slug)
    if CoopRegistry.query.filter_by(db_name=db_name).first():
        return None, "Database name collision. Choose a different coop code."

    ok, msg = _create_database(db_name)
    if not ok:
        return None, msg

    registry = CoopRegistry(
        slug=slug,
        name=name,
        db_name=db_name,
        status=form_data.get("status", "Active"),
        registration_no=(form_data.get("registration_no") or "").strip() or None,
        tin=(form_data.get("tin") or "").strip() or None,
        rdo=(form_data.get("rdo") or "").strip() or None,
        coop_type=(form_data.get("coop_type") or "").strip() or None,
        address=(form_data.get("address") or "").strip() or None,
        fiscal_year_end=(form_data.get("fiscal_year_end") or "December 31").strip(),
        contact_email=(form_data.get("contact_email") or "").strip() or None,
    )
    db.session.add(registry)
    db.session.flush()

    for key, spec in APP_MODULES.items():
        enabled = key in form_data.get("modules", []) or spec.get("default_enabled")
        db.session.add(CoopModuleSubscription(
            coop_id=registry.id,
            module_key=key,
            is_active=bool(enabled),
        ))

    db.session.commit()

    err = _init_tenant_schema(registry, form_data)
    if err:
        return registry, f"Coop registered but tenant setup warning: {err}"

    return registry, None


def _create_database(db_name):
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
        return True, None
    except Exception as exc:
        log.warning("Could not CREATE DATABASE %s: %s", db_name, exc)
        if db_name == DB_CONFIG.get("db_name"):
            return True, None
        return False, f"Could not create database '{db_name}': {exc}"


def _init_tenant_schema(registry, form_data):
    from app import db
    from app.models import Cooperative, User
    from app.services import seed_tenant_database
    from app.tenant_manager import TENANT_BIND, switch_tenant_bind

    try:
        switch_tenant_bind(registry.slug)
        db.create_all()

        coop = Cooperative(
            name=registry.name,
            registration_no=registry.registration_no,
            tin=registry.tin,
            rdo=registry.rdo,
            coop_type=registry.coop_type,
            address=registry.address,
            fiscal_year_end=registry.fiscal_year_end,
        )
        db.session.add(coop)

        admin_user = form_data.get("admin_username", "").strip()
        admin_pass = form_data.get("admin_password", "").strip()
        admin_name = form_data.get("admin_fullname", "").strip() or "Coop Administrator"

        if admin_user and admin_pass:
            db.session.add(User(
                username=admin_user,
                full_name=admin_name,
                email=form_data.get("admin_email", "").strip() or None,
                role="Admin",
                status="Active",
                password_hash=generate_password_hash(admin_pass),
            ))
        db.session.commit()

        seed_tenant_database(include_samples=form_data.get("seed_samples"))
        return None
    except Exception as exc:
        db.session.rollback()
        log.exception("Tenant init failed for %s", registry.slug)
        return str(exc)


def migrate_legacy_single_tenant():
    """Register existing single-tenant DB as 'demo' coop if no registry exists."""
    from app import db
    from app.config import DB_CONFIG

    if CoopRegistry.query.count() > 0:
        return

    slug = "demo"
    db_name = DB_CONFIG["db_name"]
    registry = CoopRegistry(
        slug=slug,
        name="Sample Primary Multi-Purpose Cooperative",
        db_name=db_name,
        status="Active",
        registration_no="CDA-XXXX-XXXXX",
        coop_type="Primary Multi-Purpose Cooperative",
        address="Philippines",
    )
    db.session.add(registry)
    db.session.flush()
    ensure_default_modules(registry)
    db.session.commit()
    log.info("Migrated legacy tenant as coop '%s' -> %s", slug, db_name)
