"""Content builders for BIR CAS mandatory technical requirements."""

import platform
import sys

from app import db
from app.audit_service import audit_trail_rows
from app.bir_cas_config import (
    BIR_CAS_CHECKLIST,
    BIR_CAS_REQUIREMENTS,
    BIR_REFERENCE,
    BIR_REFERENCE_URL,
    DATABASE_PLATFORM,
    SAMPLE_LAYOUT_REPORTS,
    SOFTWARE_TYPE,
    SYSTEM_NAME,
    SYSTEM_RELEASE,
    SYSTEM_VERSION,
    TECH_STACK,
)
from app.config import USER_ROLES, can_post_entries, is_admin_role
from app.models import Account, AuditLog, Cooperative, JournalEntry, Member, User


from app.tenant_manager import get_current_coop


def _requirement(slug):
    for req in BIR_CAS_REQUIREMENTS:
        if req["slug"] == slug:
            return req
    return None


def system_description_context():
    coop = get_current_coop()
    return {
        "requirement": _requirement("system-description"),
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "system_release": SYSTEM_RELEASE,
        "software_type": SOFTWARE_TYPE,
        "database_platform": DATABASE_PLATFORM,
        "tech_stack": TECH_STACK,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os_platform": platform.platform(),
        "coop": coop,
        "feature_mapping": [
            {"field": "Software Name", "value": SYSTEM_NAME, "source": "bir_cas_config.SYSTEM_NAME"},
            {"field": "Version Number", "value": SYSTEM_VERSION, "source": "bir_cas_config.SYSTEM_VERSION"},
            {"field": "Release Date", "value": SYSTEM_RELEASE, "source": "bir_cas_config.SYSTEM_RELEASE"},
            {"field": "Type of Software", "value": SOFTWARE_TYPE, "source": "Annex A-3 Part I"},
            {"field": "Database Platform", "value": DATABASE_PLATFORM, "source": "PostgreSQL via SQLAlchemy"},
            {"field": "Software Provider", "value": "In-house / Cooperative IT", "source": "Cooperative maintenance"},
            {"field": "Taxpayer Name", "value": coop.name if coop else "—", "source": "cooperatives.name"},
            {"field": "TIN / RDO", "value": _format_tin_rdo(coop), "source": "cooperatives.tin, cooperatives.rdo"},
        ],
    }


def _format_tin_rdo(coop):
    if not coop:
        return "—"
    parts = []
    if coop.tin:
        parts.append(f"TIN: {coop.tin}")
    if coop.rdo:
        parts.append(f"RDO: {coop.rdo}")
    return " · ".join(parts) if parts else "Configure in cooperative profile"


def process_flows_context():
    return {
        "requirement": _requirement("process-flows"),
        "flows": [
            {
                "title": "Member Transaction → General Ledger to Financial Reports",
                "steps": [
                    "Source document (member application, deposit slip, loan voucher, receipt)",
                    "Staff posts member ledger entry (Members → Member Ledger)",
                    "System auto-generates balanced journal entry (double-entry)",
                    "Journal lines posted to Chart of Accounts (CDA standard codes)",
                    "Account balances updated in real time",
                    "Financial reports generated: Trial Balance, SFC, Operations",
                ],
                "app_routes": [
                    "/members → /members/<no>/ledger",
                    "/journal → /journal/<entry_no>",
                    "/accounts",
                    "/reports/sfc, /reports/operations, /reports/trial-balance",
                ],
            },
            {
                "title": "Manual General Journal Entry",
                "steps": [
                    "Staff creates journal entry with entry number and date",
                    "Debit and credit lines entered per active account",
                    "System validates debits equal credits before posting",
                    "Entry recorded with posted_by user stamp",
                    "Audit trail logs CREATE action",
                    "Balances reflected in Trial Balance and Ledger reports",
                ],
                "app_routes": ["/journal/new", "/journal", "/reports/general-ledger"],
            },
            {
                "title": "User Access & Audit Control",
                "steps": [
                    "User authenticates via login (session-based)",
                    "Role checked on each request (Admin, Staff, Member)",
                    "Write operations restricted to Admin/Staff",
                    "Admin-only routes for user management",
                    "All CREATE/UPDATE/DELETE logged with user, timestamp, IP",
                    "Audit trail printable for BIR submission",
                ],
                "app_routes": ["/login", "/admin/users", "/documentation/system-controls"],
            },
        ],
    }


def system_modules_context():
    modules = [
        {
            "name": "Dashboard",
            "description": "Financial overview, member counts, cash, loans, journal activity",
            "route": "/dashboard",
            "bir_module": "Management Reports",
        },
        {
            "name": "General Journal",
            "description": "Double-entry journal posting with entry numbering and validation",
            "route": "/journal",
            "bir_module": "General Ledger / Journal",
        },
        {
            "name": "Chart of Accounts",
            "description": "CDA-standard cooperative chart with account types and balances",
            "route": "/accounts",
            "bir_module": "General Ledger",
        },
        {
            "name": "Members Registry",
            "description": "Member master file, share capital, savings balances",
            "route": "/members",
            "bir_module": "Subsidiary Ledger (Members' Equity)",
        },
        {
            "name": "Member Ledger",
            "description": "Share, savings, and loan transactions with auto journal integration",
            "route": "/members/<no>/ledger",
            "bir_module": "Subsidiary Ledger",
        },
        {
            "name": "CDA Financial Reports",
            "description": "Statement of Financial Condition, Operations, Trial Balance",
            "route": "/reports",
            "bir_module": "Financial Statements",
        },
        {
            "name": "BIR Books of Accounts",
            "description": "General Journal, General Ledger, Member Subsidiary Ledger print-outs",
            "route": "/reports/general-journal",
            "bir_module": "Books of Accounts (RR 9-2009)",
        },
        {
            "name": "User Management",
            "description": "Role-based access control (Admin, Staff, Member)",
            "route": "/admin/users",
            "bir_module": "System Controls / Security",
        },
        {
            "name": "BIR CAS Documentation",
            "description": "Mandatory technical requirements per RMC 5-2021 with PDF export",
            "route": "/documentation",
            "bir_module": "Systems Documentation",
        },
    ]
    stats = {
        "accounts": Account.query.filter_by(is_active=True).count(),
        "journal_entries": JournalEntry.query.count(),
        "members": Member.query.count(),
        "users": User.query.count(),
    }
    return {
        "requirement": _requirement("system-modules"),
        "modules": modules,
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
            "Staff-only write endpoints for journal and member transactions",
            "Admin-only user management and documentation PDF generation",
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
        return "Full access including user management and all documentation"
    if can_post_entries(role):
        return "Can post journal entries and member transactions; read-only admin"
    return "Read-only access to dashboard, reports, and accounts"


def disaster_recovery_context():
    coop = get_current_coop()
    return {
        "requirement": _requirement("disaster-recovery"),
        "retention_years": 10,
        "backup_procedures": [
            "Daily automated PostgreSQL pg_dump to secure off-site storage",
            "Application logs retained with audit trail in database",
            "Database transaction log (WAL) archiving for point-in-time recovery",
            "Backup verification via monthly restore test to staging environment",
        ],
        "restoration_procedures": [
            "Identify failure scope (application, database, or full server)",
            "Restore latest verified pg_dump to PostgreSQL instance",
            "Replay WAL archives if point-in-time recovery is required",
            "Restart CoopBooks application and verify audit trail continuity",
            "Validate Trial Balance totals match pre-disaster snapshot",
        ],
        "physical_location": "Primary: cooperative server / cloud VM · Secondary: encrypted off-site backup",
        "coop": coop,
        "feature_mapping": [
            {"control": "10-year retention", "implementation": "PostgreSQL backups + audit_logs table"},
            {"control": "Archive/restore", "implementation": "pg_dump / pg_restore documented procedures"},
            {"control": "Audit trail preservation", "implementation": "audit_logs included in DB backups"},
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
    base = {
        "slug": slug,
        "title": ctx["requirement"]["title"],
        "number": ctx["requirement"]["number"],
        "bir_reference": ctx["requirement"]["bir_reference"],
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "coop_name": coop.name if coop else SYSTEM_NAME,
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
                    "python": ctx["python_version"],
                    "platform": ctx["os_platform"],
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
                {"name": m["name"], "description": m["description"], "route": m["route"]}
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
            ]),
        ]
    return base
