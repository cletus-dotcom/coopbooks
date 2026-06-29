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


def build_database_uri(db_name=None):
    target = db_name or DB_CONFIG["db_name"]
    platform_name = DB_CONFIG["platform_db_name"]
    tenant_url = os.getenv("DATABASE_URL")
    platform_url = os.getenv("PLATFORM_DATABASE_URL")

    if platform_url and target == platform_name:
        return _normalize_sqlalchemy_uri(platform_url)
    if tenant_url and not platform_url:
        # Single hosted DB (e.g. Supabase): platform + tenant tables share one database.
        return _normalize_sqlalchemy_uri(tenant_url)
    if tenant_url and target == DB_CONFIG["db_name"]:
        return _normalize_sqlalchemy_uri(tenant_url)
    if tenant_url and target == platform_name:
        return _uri_with_db_name(_normalize_sqlalchemy_uri(tenant_url), platform_name)

    return (
        f"postgresql+psycopg2://{quote(DB_CONFIG['db_user'], safe='')}:"
        f"{quote(DB_CONFIG['db_pass'], safe='')}@"
        f"{DB_CONFIG['db_ip']}:{DB_CONFIG['db_port']}/{quote(target, safe='')}"
    )


def is_platform_admin_session(session_obj):
    return bool(session_obj.get("is_platform_admin"))


def can_manage_coops(session_obj):
    return is_platform_admin_session(session_obj)

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
    value = (role or "Member").strip().capitalize()
    legacy = {"Bookkeeper": "Staff", "Viewer": "Member", "Employee": "Member", "User": "Member"}
    if value in legacy:
        return legacy[value]
    return value if value in USER_ROLES else "Member"


def is_valid_user_role(role):
    return normalize_role(role) in USER_ROLES


def is_admin_role(role=None):
    return normalize_role(role).lower() == "admin"


def can_post_entries(role=None):
    return normalize_role(role).lower() in ("admin", "staff")


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
