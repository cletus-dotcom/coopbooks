"""Content builders for BIR CAS mandatory technical requirements."""

import platform
import sys

from app.audit_service import audit_trail_rows
from app.bir_cas_config import (
    BIR_CAS_CHECKLIST,
    BIR_CAS_REQUIREMENTS,
    BIR_EXTRA_MODULES,
    BIR_MODULE_CLASSIFICATION,
    BIR_REFERENCE,
    BIR_REFERENCE_URL,
    DATABASE_PLATFORM,
    DEPLOYMENT_MODEL,
    HOSTING_OPTIONS,
    SAMPLE_LAYOUT_REPORTS,
    SOFTWARE_TYPE,
    SYSTEM_NAME,
    SYSTEM_RELEASE,
    SYSTEM_VERSION,
    TECH_STACK,
    WEB_SERVER,
)
from app.config import USER_ROLES, can_post_entries, is_admin_role
from app.models import Account, AuditLog, JournalEntry, Member, User
from app.modules_config import APP_MODULES
from app.tenant_manager import get_coop_registry, get_current_coop


def _requirement(slug):
    for req in BIR_CAS_REQUIREMENTS:
        if req["slug"] == slug:
            return req
    return None


def _registry_profile(coop, registry):
    """Cooperative identity fields for BIR Annex A-3."""
    name = (coop.name if coop else None) or (registry.name if registry else None) or "—"
    registration_no = (getattr(coop, "registration_no", None) or (registry.registration_no if registry else None))
    tin = (getattr(coop, "tin", None) or (registry.tin if registry else None))
    rdo = (getattr(coop, "rdo", None) or (registry.rdo if registry else None))
    address = (getattr(coop, "address", None) or (registry.address if registry else None))
    return {
        "name": name,
        "registration_no": registration_no,
        "tin": tin,
        "rdo": rdo,
        "address": address,
    }


def _format_tin_rdo(profile):
    parts = []
    if profile.get("tin"):
        parts.append(f"TIN: {profile['tin']}")
    if profile.get("rdo"):
        parts.append(f"RDO: {profile['rdo']}")
    return " · ".join(parts) if parts else "Configure in cooperative profile"


def _documented_modules():
    modules = []
    for key, spec in APP_MODULES.items():
        if key == "bir_cas":
            continue
        meta = BIR_MODULE_CLASSIFICATION.get(key, {})
        route = spec["route_prefixes"][0] if spec.get("route_prefixes") else "—"
        modules.append({
            "name": spec["label"],
            "description": meta.get("description", spec["label"]),
            "route": route,
            "bir_module": meta.get("bir_module", "Application Module"),
            "subscription": not spec.get("core", False),
        })
    modules.extend(BIR_EXTRA_MODULES)
    return modules


def system_description_context():
    coop = get_current_coop()
    registry = get_coop_registry()
    profile = _registry_profile(coop, registry)
    return {
        "requirement": _requirement("system-description"),
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "system_release": SYSTEM_RELEASE,
        "software_type": SOFTWARE_TYPE,
        "database_platform": DATABASE_PLATFORM,
        "tech_stack": TECH_STACK,
        "deployment_model": DEPLOYMENT_MODEL,
        "hosting_options": HOSTING_OPTIONS,
        "web_server": WEB_SERVER,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os_platform": platform.platform(),
        "coop": coop,
        "registry": registry,
        "feature_mapping": [
            {"field": "Software Name", "value": SYSTEM_NAME, "source": "CoopBooks application"},
            {"field": "Version Number", "value": SYSTEM_VERSION, "source": "Release tag"},
            {"field": "Release Date", "value": SYSTEM_RELEASE, "source": "Annex A-3 Part I"},
            {"field": "Type of Software", "value": SOFTWARE_TYPE, "source": "Annex A-3 Part I"},
            {"field": "Deployment Model", "value": DEPLOYMENT_MODEL, "source": "Single cooperative installation"},
            {"field": "Hosting Environment", "value": HOSTING_OPTIONS, "source": "On-premises or cloud computing"},
            {"field": "Database Platform", "value": DATABASE_PLATFORM, "source": "PostgreSQL via SQLAlchemy"},
            {"field": "Application Server", "value": WEB_SERVER, "source": "Production WSGI host"},
            {"field": "Software Provider", "value": "In-house / Cooperative IT", "source": "Cooperative maintenance"},
            {"field": "Taxpayer Name", "value": profile["name"], "source": "Cooperative registry profile"},
            {"field": "CDA Registration No.", "value": profile["registration_no"] or "—", "source": "coop_registry.registration_no"},
            {"field": "TIN / RDO", "value": _format_tin_rdo(profile), "source": "coop_registry.tin, coop_registry.rdo"},
            {"field": "Business Address", "value": profile["address"] or "—", "source": "coop_registry.address"},
        ],
    }


def process_flows_context():
    return {
        "requirement": _requirement("process-flows"),
        "flows": [
            {
                "title": "Member Registration and Ledger Posting",
                "steps": [
                    "Staff registers member in Members Registry (CDA MC 2012-16 fields)",
                    "Member share capital, savings, and loan balances maintained in master file",
                    "Staff posts member ledger transaction (share, savings, loan, or other)",
                    "System validates amounts and auto-generates balanced journal entry",
                    "Journal lines posted to Chart of Accounts (CDA standard codes)",
                    "Member Subsidiary Ledger and General Ledger updated in real time",
                    "Audit trail records CREATE action with user and timestamp",
                ],
                "app_routes": [
                    "/members",
                    "/members/<no>/ledger",
                    "/journal",
                    "/reports/member-subsidiary",
                ],
            },
            {
                "title": "Manual General Journal Entry",
                "steps": [
                    "Staff creates journal entry with entry number and transaction date",
                    "Debit and credit lines entered per active chart-of-accounts code",
                    "System validates debits equal credits before posting",
                    "Entry recorded with posted_by user stamp",
                    "Audit trail logs CREATE action",
                    "Balances reflected in Trial Balance, General Ledger, and CDA reports",
                ],
                "app_routes": [
                    "/journal/new",
                    "/journal",
                    "/reports/general-ledger",
                    "/reports/trial-balance",
                ],
            },
            {
                "title": "CDA and BIR Financial Reporting",
                "steps": [
                    "Posted journal entries accumulate account balances",
                    "Staff opens Reports → CDA Reports for Statement of Financial Condition and Operations",
                    "Staff opens Reports → BIR Books of Accounts for RR 9-2009 layouts",
                    "Reports display cooperative name, TIN, and uploaded logo on print/PDF",
                    "PDF export available for each book and CAS requirement section",
                ],
                "app_routes": [
                    "/reports/cda",
                    "/reports/bir-books",
                    "/documentation",
                ],
            },
            {
                "title": "User Access, Module Control, and Audit Trail",
                "steps": [
                    "User authenticates via login (session-based, password hashing)",
                    "Role checked on each request (Admin, Staff, or Member)",
                    "Write operations restricted to Admin and Staff roles",
                    "Admin-only routes for user management (/admin/users)",
                    "Optional feature modules gated by cooperative subscription",
                    "All CREATE/UPDATE/DELETE logged with user, timestamp, entity, and IP",
                    "Audit trail viewable and printable for BIR submission",
                ],
                "app_routes": [
                    "/login",
                    "/admin/users",
                    "/documentation/audit-trail",
                    "/documentation/system-controls",
                ],
            },
        ],
    }


def system_modules_context():
    stats = {
        "accounts": Account.query.filter_by(is_active=True).count(),
        "journal_entries": JournalEntry.query.count(),
        "members": Member.query.count(),
        "users": User.query.count(),
    }
    return {
        "requirement": _requirement("system-modules"),
        "modules": _documented_modules(),
        "stats": stats,
    }


def sample_layouts_context():
    return {
        "requirement": _requirement("sample-layouts"),
        "reports": SAMPLE_LAYOUT_REPORTS,
        "books_declared": [
            {"name": "General Journal", "method": "Electronic", "location": "Head Office"},
            {"name": "General Ledger", "method": "Electronic", "location": "Head Office"},
            {"name": "Trial Balance", "method": "Electronic", "location": "Head Office"},
            {"name": "Member Subsidiary Ledger", "method": "Electronic", "location": "Head Office"},
            {"name": "Statement of Financial Condition", "method": "Electronic", "location": "Head Office"},
            {"name": "Statement of Operations", "method": "Electronic", "location": "Head Office"},
        ],
    }


def system_controls_context():
    roles_detail = []
    for role in USER_ROLES:
        roles_detail.append({
            "role": role,
            "can_login": True,
            "can_post": can_post_entries(role),
            "is_admin": is_admin_role(role),
            "restrictions": _role_restrictions(role),
        })

    recent_audit = audit_trail_rows(limit=25)
    return {
        "requirement": _requirement("system-controls"),
        "roles": roles_detail,
        "security_controls": [
            "Session-based authentication with password hashing (Werkzeug PBKDF2)",
            "Route guards on all protected endpoints (app/auth.py)",
            "Role normalization and inactive account blocking",
            "Admin and Staff write access for journal and member transactions",
            "Admin-only user management at /admin/users",
            "Optional feature modules gated by cooperative subscription",
            "Cooperative profile stores TIN, RDO, and logo used on reports and PDFs",
            "Audit trail with timestamp, user, action, entity, and IP address",
            "Double-entry validation — debits must equal credits before posting",
            "Journal entry numbers are unique and sequential per fiscal year",
        ],
        "annex_b_compliance": [
            {"item": "Generates printable audit trail / activity log", "compliant": True},
            {"item": "Records user who created/updated data", "compliant": True},
            {"item": "Application access protected with authentication", "compliant": True},
            {"item": "Database record modification logged", "compliant": True},
            {"item": "Role-based access restrictions", "compliant": True},
        ],
        "recent_audit": recent_audit,
        "audit_total": AuditLog.query.count(),
    }


def _role_restrictions(role):
    if is_admin_role(role):
        return "Full cooperative access including user management and all subscribed modules"
    if can_post_entries(role):
        return "Can post journal entries and member transactions; cannot manage users"
    return "Read-only access to dashboard, reports, and accounts"


def disaster_recovery_context():
    coop = get_current_coop()
    registry = get_coop_registry()
    profile = _registry_profile(coop, registry)
    return {
        "requirement": _requirement("disaster-recovery"),
        "retention_years": 10,
        "backup_procedures": [
            "Daily automated PostgreSQL pg_dump to secure off-site storage",
            "Database hosted on-premises or in a cloud computing environment with encrypted connections",
            "Application audit trail stored in PostgreSQL and included in backups",
            "Database write-ahead log (WAL) archiving for point-in-time recovery when enabled",
            "Monthly restore test to a staging environment to verify backup integrity",
        ],
        "restoration_procedures": [
            "Identify failure scope (application host, database, or full site)",
            "Restore latest verified pg_dump to a PostgreSQL instance (local or cloud)",
            "Replay WAL archives if point-in-time recovery is required",
            "Redeploy CoopBooks on the application server and verify HTTPS access",
            "Confirm audit trail continuity and validate Trial Balance against pre-disaster totals",
        ],
        "physical_location": (
            f"Primary: cooperative head office or cloud computing environment · "
            f"Secondary: encrypted off-site backup (cloud storage or physical media)"
        ),
        "coop": coop,
        "profile": profile,
        "feature_mapping": [
            {"control": "10-year retention", "implementation": "PostgreSQL backups + audit_logs table"},
            {"control": "Archive/restore", "implementation": "pg_dump / pg_restore documented procedures"},
            {"control": "Audit trail preservation", "implementation": "audit_logs included in database backups"},
            {"control": "Off-site copy", "implementation": "Encrypted backup to separate cloud or media location"},
        ],
    }


def documentation_index_context():
    return {
        "requirements": BIR_CAS_REQUIREMENTS,
        "checklist": BIR_CAS_CHECKLIST,
        "bir_reference": BIR_REFERENCE,
        "bir_reference_url": BIR_REFERENCE_URL,
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "deployment_model": DEPLOYMENT_MODEL,
    }


def context_for_slug(slug):
    builders = {
        "system-description": system_description_context,
        "process-flows": process_flows_context,
        "system-modules": system_modules_context,
        "sample-layouts": sample_layouts_context,
        "system-controls": system_controls_context,
        "disaster-recovery": disaster_recovery_context,
    }
    builder = builders.get(slug)
    if not builder:
        return None
    ctx = builder()
    ctx["bir_reference"] = BIR_REFERENCE
    ctx["bir_reference_url"] = BIR_REFERENCE_URL
    ctx["system_name"] = SYSTEM_NAME
    ctx["system_version"] = SYSTEM_VERSION
    ctx["coop"] = get_current_coop()
    return ctx


def pdf_data_for_slug(slug):
    """Return structured data for PDF generation."""
    ctx = context_for_slug(slug)
    if not ctx:
        return None

    coop = get_current_coop()
    registry = get_coop_registry()
    profile = _registry_profile(coop, registry)
    base = {
        "slug": slug,
        "title": ctx["requirement"]["title"],
        "number": ctx["requirement"]["number"],
        "bir_reference": ctx["requirement"]["bir_reference"],
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "coop_name": profile["name"],
        "generated_for": "BIR CAS Registration — RMC No. 5-2021",
    }

    if slug == "system-description":
        base["sections"] = [
            ("System Identification", ctx["feature_mapping"]),
            ("Technical Stack", [
                {"field": k.replace("_", " ").title(), "value": v}
                for k, v in {
                    "tech_stack": TECH_STACK,
                    "database": DATABASE_PLATFORM,
                    "deployment": DEPLOYMENT_MODEL,
                    "hosting": HOSTING_OPTIONS,
                    "web_server": WEB_SERVER,
                    "python": ctx["python_version"],
                }.items()
            ]),
        ]
    elif slug == "process-flows":
        base["sections"] = [
            (flow["title"], [{"step": s} for s in flow["steps"]])
            for flow in ctx["flows"]
        ]
    elif slug == "system-modules":
        base["sections"] = [
            ("Registered Modules", [
                {
                    "name": m["name"],
                    "description": m["description"],
                    "route": m["route"],
                    "bir_module": m["bir_module"],
                }
                for m in ctx["modules"]
            ]),
        ]
    elif slug == "sample-layouts":
        base["sections"] = [
            ("Books of Accounts Declared", ctx["books_declared"]),
        ]
        base["include_sample_data"] = True
    elif slug == "system-controls":
        base["sections"] = [
            ("User Roles", ctx["roles"]),
            ("Security Controls", [{"control": c} for c in ctx["security_controls"]]),
            ("Annex B Compliance", ctx["annex_b_compliance"]),
        ]
        base["audit_rows"] = audit_trail_rows(limit=100)
    elif slug == "disaster-recovery":
        base["sections"] = [
            ("Backup Procedures", [{"step": s} for s in ctx["backup_procedures"]]),
            ("Restoration Procedures", [{"step": s} for s in ctx["restoration_procedures"]]),
            ("Retention & Location", [
                {"field": "Retention Period", "value": f"{ctx['retention_years']} years"},
                {"field": "Physical Location", "value": ctx["physical_location"]},
                {"field": "Taxpayer", "value": profile["name"]},
            ]),
        ]
    return base
