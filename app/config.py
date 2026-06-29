import os
from urllib.parse import quote, unquote, urlparse, urlunparse


def _env(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


DB_CONFIG = {
    "db_user": _env("DB_USER", "POSTGRES_USER", default="postgres"),
    "db_pass": _env("DB_PASS", "POSTGRES_PASSWORD", default="password"),
    "db_ip": _env("DB_IP", "DB_HOST", "POSTGRES_HOST", default="127.0.0.1"),
    "db_port": _env("DB_PORT", "POSTGRES_PORT", default="5432"),
    "db_name": _env("DB_NAME", default="coop_accounting"),
    "platform_db_name": _env("PLATFORM_DB_NAME", default="coop_platform"),
}


def is_serverless_host():
    return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _normalize_sqlalchemy_uri(url):
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def _uri_with_db_name(uri, db_name):
    parsed = urlparse(uri.replace("postgresql+psycopg2://", "postgresql://", 1))
    safe_name = quote(unquote(db_name), safe="")
    return urlunparse(parsed._replace(path=f"/{safe_name}")).replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )


def _is_supabase_direct_url(url):
    if not url:
        return False
    lowered = url.lower()
    return "db." in lowered and ".supabase.co" in lowered and "pooler.supabase.com" not in lowered


def _is_supabase_pooler_url(url):
    if not url:
        return False
    lowered = url.lower()
    return "pooler.supabase.com" in lowered or ":6543/" in lowered or lowered.rstrip().endswith(":6543")


def _effective_database_url():
    """Prefer pooler URL on Vercel/serverless (required for Supabase)."""
    import logging

    logger = logging.getLogger(__name__)
    pooler = os.getenv("DATABASE_POOLER_URL")
    direct = os.getenv("DATABASE_URL")

    if pooler:
        return pooler
    if direct and _is_supabase_pooler_url(direct):
        return direct
    if is_serverless_host() and direct and _is_supabase_direct_url(direct):
        logger.error(
            "DATABASE_URL uses Supabase direct host (db.*.supabase.co:5432) which fails on Vercel. "
            "In Vercel env vars, REPLACE DATABASE_URL with the Supabase Transaction pooler URI "
            "(host: aws-0-*.pooler.supabase.com, port 6543), or set DATABASE_POOLER_URL."
        )
        return None
    return direct


def database_config_error():
    """Human-readable message when serverless DB env is misconfigured."""
    if not is_serverless_host():
        return None
    url = _effective_database_url()
    if url:
        return None
    if os.getenv("DATABASE_URL") and _is_supabase_direct_url(os.getenv("DATABASE_URL")):
        return (
            "Database misconfigured: use Supabase pooler URL (port 6543), not db.*.supabase.co."
        )
    if not os.getenv("DATABASE_URL") and not os.getenv("DATABASE_POOLER_URL"):
        return "Database misconfigured: set DATABASE_URL to your Supabase pooler connection string."
    return None


def build_database_uri(db_name=None):
    """Single-database URI for this installation."""
    url = _effective_database_url()
    if url:
        return _normalize_sqlalchemy_uri(url)

    target = db_name or DB_CONFIG["db_name"]
    if is_serverless_host():
        return "postgresql+psycopg2://127.0.0.1:1/__misconfigured__"

    return (
        f"postgresql+psycopg2://{quote(DB_CONFIG['db_user'], safe='')}:"
        f"{quote(DB_CONFIG['db_pass'], safe='')}@"
        f"{DB_CONFIG['db_ip']}:{DB_CONFIG['db_port']}/{quote(target, safe='')}"
    )


def sqlalchemy_engine_options():
    """Serverless-friendly pool settings."""
    opts = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    if is_serverless_host():
        opts.update({
            "pool_size": 1,
            "max_overflow": 0,
        })
    return opts


def is_platform_admin_role(role=None):
    return (role or "").strip().lower() == "platformadmin"


def is_platform_admin_session(session_obj):
    return is_platform_admin_role(session_obj.get("role"))


def can_manage_coops(session_obj=None, role=None):
    if session_obj is not None and role is None:
        role = session_obj.get("role")
    return is_platform_admin_role(role)


ASSIGNABLE_ROLES = ["Admin", "Staff", "Member"]
ALL_USER_ROLES = ["PlatformAdmin"] + ASSIGNABLE_ROLES


def assignable_user_roles(current_role):
    if is_platform_admin_role(current_role):
        return list(ALL_USER_ROLES)
    return list(ASSIGNABLE_ROLES)

SECRET_KEY = os.getenv("SECRET_KEY", "coop_cda_secret_key")

# CDA / cooperative brand colors
COOP_GREEN = "#1B5E20"
COOP_GREEN_DARK = "#0D3B12"
COOP_GREEN_LIGHT = "#2E7D32"
COOP_GOLD = "#F9A825"

USER_ROLES = ["Admin", "Staff", "Member"]

CDA_REPORT_FORMS = [
    {
        "code": "Annex A",
        "title": "Statement of Financial Condition",
        "source": "MC 2022-24",
        "url": "https://cda.gov.ph/wp-content/uploads/2022/11/Annexes-under-MC-2022-24.pdf",
    },
    {
        "code": "Annex B",
        "title": "Statement of Operations",
        "source": "MC 2022-24",
        "url": "https://cda.gov.ph/wp-content/uploads/2022/11/Annexes-under-MC-2022-24.pdf",
    },
    {
        "code": "Annex E",
        "title": "Statement of Cash Flows",
        "source": "MC 2022-24",
        "url": "https://cda.gov.ph/wp-content/uploads/2022/11/Annexes-under-MC-2022-24.pdf",
    },
    {
        "code": "CAPR",
        "title": "Cooperative Annual Progress Report",
        "source": "CDA CAIS",
        "url": "https://cda.gov.ph/downloads/cooperative-standard-report-forms/",
    },
]


def normalize_role(role):
    value = (role or "Member").strip()
    if value.lower() == "platformadmin":
        return "PlatformAdmin"
    value = value.capitalize()
    legacy = {"Bookkeeper": "Staff", "Viewer": "Member", "Employee": "Member", "User": "Member"}
    if value in legacy:
        return legacy[value]
    return value if value in ALL_USER_ROLES else "Member"


def is_valid_user_role(role):
    return normalize_role(role) in ALL_USER_ROLES


def is_admin_role(role=None):
    return normalize_role(role) == "Admin"


def can_post_entries(role=None):
    normalized = normalize_role(role)
    return normalized in ("Admin", "Staff", "PlatformAdmin")


def safe_login_redirect(next_param, default_endpoint="main_routes.dashboard"):
    from flask import url_for

    if not next_param:
        return url_for(default_endpoint)

    value = next_param.strip()
    if not value.startswith("/") or value.startswith("//"):
        return url_for(default_endpoint)

    allowed_prefixes = (
        "/dashboard", "/journal", "/accounts", "/members", "/reports",
        "/admin", "/documentation", "/about",
    )
    if any(value.startswith(prefix) for prefix in allowed_prefixes):
        return value
    return url_for(default_endpoint)
