"""Provision the single cooperative for this installation."""

import logging

from werkzeug.security import generate_password_hash

from app.config import DB_CONFIG
from app.modules_config import APP_MODULES
from app.platform_models import CoopModuleSubscription, CoopRegistry
from app.tenant_manager import db_name_for_slug, ensure_default_modules, is_valid_slug, normalize_slug

log = logging.getLogger(__name__)


def provision_coop(form_data):
    """Register the cooperative profile and seed the local database."""
    from app import db

    if CoopRegistry.query.count() > 0:
        return None, (
            "A cooperative is already registered. "
            "Use Cooperative Settings to update the profile."
        )

    slug = normalize_slug(form_data.get("slug", ""))
    name = (form_data.get("name") or "").strip()
    if not is_valid_slug(slug):
        return None, "Coop code must be 3–40 characters (lowercase letters, numbers, hyphens)."
    if not name:
        return None, "Cooperative name is required."

    registry = CoopRegistry(
        slug=slug,
        name=name,
        db_name=db_name_for_slug(slug),
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

    err = _init_coop_data(registry, form_data)
    if err:
        return registry, f"Coop registered with warnings: {err}"

    return registry, None


def _init_coop_data(registry, form_data):
    from app import db
    from app.models import Cooperative, User
    from app.services import seed_tenant_database

    try:
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
        log.exception("Coop setup failed for %s", registry.slug)
        return str(exc)


def migrate_legacy_single_tenant():
    """Ensure a registry row exists for legacy single-coop databases."""
    from app import db

    if CoopRegistry.query.count() > 0:
        return

    slug = "demo"
    registry = CoopRegistry(
        slug=slug,
        name="Sample Primary Multi-Purpose Cooperative",
        db_name=DB_CONFIG["db_name"],
        status="Active",
        registration_no="CDA-XXXX-XXXXX",
        coop_type="Primary Multi-Purpose Cooperative",
        address="Philippines",
    )
    db.session.add(registry)
    db.session.flush()
    ensure_default_modules(registry)
    db.session.commit()
    log.info("Registered legacy cooperative as '%s'", slug)
