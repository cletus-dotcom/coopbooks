import os

DB_CONFIG = {
    "db_user": os.getenv("DB_USER", "postgres"),
    "db_pass": os.getenv("DB_PASS", "password"),
    "db_ip": os.getenv("DB_IP", "127.0.0.1"),
    "db_port": os.getenv("DB_PORT", "5432"),
    "db_name": os.getenv("DB_NAME", "coop_accounting"),
    "platform_db_name": os.getenv("PLATFORM_DB_NAME", "coop_platform"),
}


def build_database_uri(db_name=None):
    name = db_name or DB_CONFIG["db_name"]
    return (
        f"postgresql+psycopg2://{DB_CONFIG['db_user']}:{DB_CONFIG['db_pass']}@"
        f"{DB_CONFIG['db_ip']}:{DB_CONFIG['db_port']}/{name}"
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
