"""Single-tenant cooperative context and registry helpers."""

import re

from flask import url_for

from app.modules_config import APP_MODULES, default_module_keys
from app.platform_models import CoopModuleSubscription, CoopRegistry

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")

LOGO_MIME_BY_EXT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


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


def get_coop_registry():
    """The single registered cooperative for this installation."""
    return (
        CoopRegistry.query.filter_by(status="Active").order_by(CoopRegistry.id).first()
        or CoopRegistry.query.order_by(CoopRegistry.id).first()
    )


def get_registry_from_session():
    return get_coop_registry()


def get_current_coop():
    """Cooperative profile row (accounting entity)."""
    from app.models import Cooperative

    registry = get_coop_registry()
    coop = Cooperative.query.first()
    if coop:
        return coop
    if registry:
        return _registry_as_cooperative(registry)
    return None


def _registry_as_cooperative(registry):
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
    registry = get_coop_registry()
    coop_id = coop_id or (registry.id if registry else None)
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
        from app import db

        db.session.add(CoopModuleSubscription(
            coop_id=coop.id,
            module_key=key,
            is_active=APP_MODULES[key].get("default_enabled", False),
        ))


def coop_has_logo(registry=None):
    registry = registry or get_coop_registry()
    return bool(registry and registry.logo_data)


def coop_logo_url(registry=None):
    if coop_has_logo(registry):
        return url_for("main_routes.coop_logo")
    return url_for("static", filename="images/coop_logo.svg")


def store_coop_logo(registry, file_bytes, filename):
    """Persist logo bytes on the registry row."""
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    registry.logo_data = file_bytes
    registry.logo_mime_type = LOGO_MIME_BY_EXT.get(ext, "application/octet-stream")
    registry.logo_filename = f"logo.{ext}" if ext else "logo.bin"


def list_active_coops():
    registry = get_coop_registry()
    return [registry] if registry and registry.status == "Active" else []
