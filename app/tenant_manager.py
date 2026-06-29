"""Multi-tenant database routing and coop context."""

import re
from pathlib import Path

from flask import current_app, g, session, url_for

from app.config import DB_CONFIG, build_database_uri
from app.modules_config import APP_MODULES, default_module_keys
from app.platform_models import CoopModuleSubscription, CoopRegistry

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
TENANT_BIND = "tenant"
UPLOAD_ROOT = Path(__file__).parent.parent / "static" / "uploads" / "coops"


def normalize_slug(value):
    slug = (value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:40]


def is_valid_slug(slug):
    return bool(slug and SLUG_RE.match(slug))


def db_name_for_slug(slug):
    safe = slug.replace("-", "_")
    return f"coop_{safe}"[:63]


def switch_tenant_bind(slug):
    """Point the tenant SQLAlchemy bind at the coop database."""
    from app import db

    registry = CoopRegistry.query.filter_by(slug=slug).first()
    if not registry:
        raise ValueError(f"Unknown cooperative: {slug}")

    uri = build_database_uri(registry.db_name)
    binds = dict(current_app.config.get("SQLALCHEMY_BINDS") or {})
    binds[TENANT_BIND] = uri
    current_app.config["SQLALCHEMY_BINDS"] = binds
    db.session.remove()

    g.coop_registry = registry
    g.coop_slug = slug
    return registry


def get_registry_from_session():
    slug = session.get("coop_slug")
    if not slug or session.get("is_platform_admin"):
        return None
    return CoopRegistry.query.filter_by(slug=slug).first()


def get_current_coop():
    """Tenant-local Cooperative profile row."""
    from app.models import Cooperative

    registry = get_registry_from_session()
    if registry:
        coop = Cooperative.query.first()
        if coop:
            return coop
        return _registry_as_cooperative(registry)

    if hasattr(g, "coop_registry") and g.coop_registry:
        return _registry_as_cooperative(g.coop_registry)

    return Cooperative.query.first()


def _registry_as_cooperative(registry):
    """Lightweight coop-like object from platform registry."""

    class CoopView:
        pass

    view = CoopView()
    view.id = registry.id
    view.name = registry.name
    view.registration_no = registry.registration_no
    view.tin = registry.tin
    view.rdo = registry.rdo
    view.coop_type = registry.coop_type
    view.address = registry.address
    view.fiscal_year_end = registry.fiscal_year_end
    view.logo_filename = registry.logo_filename
    view.contact_email = registry.contact_email
    view.slug = registry.slug
    return view


def subscribed_module_keys(coop_id=None):
    slug = session.get("coop_slug")
    if coop_id is None and slug:
        registry = CoopRegistry.query.filter_by(slug=slug).first()
        coop_id = registry.id if registry else None

    if coop_id is None:
        return default_module_keys()

    rows = CoopModuleSubscription.query.filter_by(
        coop_id=coop_id, is_active=True
    ).all()
    if not rows:
        return default_module_keys()
    return [row.module_key for row in rows]


def coop_has_module(module_key, coop_id=None):
    return module_key in subscribed_module_keys(coop_id)


def ensure_default_modules(coop):
    existing = {m.module_key for m in coop.modules}
    for key in APP_MODULES:
        if key in existing:
            continue
        db_add = CoopModuleSubscription(
            coop_id=coop.id,
            module_key=key,
            is_active=APP_MODULES[key].get("default_enabled", False),
        )
        from app import db
        db.session.add(db_add)


def coop_logo_url(registry=None):
    registry = registry or get_registry_from_session()
    if registry and registry.logo_filename:
        return url_for(
            "main_routes.coop_logo",
            slug=registry.slug,
            filename=registry.logo_filename,
        )
    return url_for("static", filename="images/coop_logo.svg")


def coop_upload_dir(slug):
    path = UPLOAD_ROOT / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_active_coops():
    return CoopRegistry.query.filter_by(status="Active").order_by(CoopRegistry.name).all()
