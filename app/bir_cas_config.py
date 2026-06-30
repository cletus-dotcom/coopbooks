"""BIR CAS registration requirements per RMC No. 5-2021."""

SYSTEM_NAME = "CoopBooks"
SYSTEM_VERSION = "1.0.0"
SYSTEM_RELEASE = "2025-06-01"
SOFTWARE_TYPE = "Customized cooperative accounting system"
DATABASE_PLATFORM = "PostgreSQL 14+ (single cooperative database)"
TECH_STACK = "Python 3.12+, Flask 3.x, SQLAlchemy, ReportLab, Bootstrap 5"
DEPLOYMENT_MODEL = "Single cooperative · Web application (browser access)"
HOSTING_OPTIONS = (
    "On-premises Linux/Windows server or cloud computing environment "
    "(managed VM with PostgreSQL and HTTPS reverse proxy)"
)
WEB_SERVER = "Gunicorn or Waitress (production WSGI)"
BIR_REFERENCE = "RMC No. 5-2021 (Annex A, A-3, B)"
BIR_REFERENCE_URL = (
    "https://www.bir.gov.ph/images/bir_files/internal_communications_2/"
    "RMC%20No.%205-2021.pdf"
)

BIR_CAS_REQUIREMENTS = [
    {
        "slug": "system-description",
        "number": 1,
        "title": "System Description",
        "short_title": "System Description",
        "icon": "bi-pc-display",
        "bir_reference": "Annex A-3 Part I",
        "description": (
            "System name, software and hardware used, and system version. "
            "Per RMC 5-2021 this is declared in the Summary of System Description "
            "(Annex A-3) submitted with the Sworn Statement."
        ),
    },
    {
        "slug": "process-flows",
        "number": 2,
        "title": "Process Flows",
        "short_title": "Process Flows",
        "icon": "bi-diagram-3",
        "bir_reference": "Annex A-3 / Annex B",
        "description": (
            "Detailed flow of transactions from source documents through posting "
            "to financial reports, showing how data integrity is maintained."
        ),
    },
    {
        "slug": "system-modules",
        "number": 3,
        "title": "List of System Modules",
        "short_title": "System Modules",
        "icon": "bi-grid-3x3-gap",
        "bir_reference": "Annex A-3 Part III",
        "description": (
            "Complete list of CoopBooks features: dashboard, general journal, "
            "chart of accounts, member registry, CDA/BIR reports, and system controls."
        ),
    },
    {
        "slug": "sample-layouts",
        "number": 4,
        "title": "Sample Layouts",
        "short_title": "Sample Layouts",
        "icon": "bi-file-earmark-spreadsheet",
        "bir_reference": "Annex A CDR Item 3 / RR No. 9-2009",
        "description": (
            "Sample print-outs of Books of Accounts and BIR-required reports: "
            "General Journal, General Ledger, Trial Balance, and Member Subsidiary Ledger."
        ),
    },
    {
        "slug": "system-controls",
        "number": 5,
        "title": "System Controls",
        "short_title": "System Controls",
        "icon": "bi-shield-lock",
        "bir_reference": "Annex B Items 8, 11–12",
        "description": (
            "User access levels, restrictions, and built-in audit trails recording "
            "who created, edited, or deleted transactions."
        ),
    },
    {
        "slug": "disaster-recovery",
        "number": 6,
        "title": "Disaster Recovery Plan",
        "short_title": "Disaster Recovery",
        "icon": "bi-cloud-arrow-up",
        "bir_reference": "Annex A-3 Part VIII / Annex B Item 7",
        "description": (
            "Procedures for PostgreSQL backup, restoration, and ten-year record retention "
            "pursuant to RR No. 17-2013 as amended by RR No. 5-2014."
        ),
    },
]

BIR_CAS_CHECKLIST = [
    {"item": "Sworn Statement (Annex A-1 or A-2) with Annex A-3", "doc_slug": "system-description"},
    {"item": "Sample print-out of Books of Accounts", "doc_slug": "sample-layouts"},
    {"item": "Printed copy of Audit Trail", "doc_slug": "system-controls"},
    {"item": "Signed Annex B — Standard Functional & Technical Requirements", "doc_slug": "system-controls"},
]

SAMPLE_LAYOUT_REPORTS = [
    {
        "slug": "general-journal",
        "title": "General Journal",
        "route": "main_routes.report_general_journal",
        "bir_form": "Book of Accounts — General Journal",
    },
    {
        "slug": "general-ledger",
        "title": "General Ledger",
        "route": "main_routes.report_general_ledger",
        "bir_form": "Book of Accounts — General Ledger",
    },
    {
        "slug": "trial-balance",
        "title": "Trial Balance",
        "route": "main_routes.report_trial_balance",
        "bir_form": "Trial Balance",
    },
    {
        "slug": "member-subsidiary",
        "title": "Member Subsidiary Ledger",
        "route": "main_routes.report_member_subsidiary",
        "bir_form": "Subsidiary Ledger (Member Share/Savings)",
    },
]

BIR_MODULE_CLASSIFICATION = {
    "dashboard": {
        "bir_module": "Management Reports",
        "description": "Financial overview, member counts, cash, loans, and recent journal activity.",
    },
    "journal": {
        "bir_module": "General Ledger / Journal",
        "description": "Double-entry journal posting with entry numbering, validation, and audit logging.",
    },
    "accounts": {
        "bir_module": "General Ledger",
        "description": "CDA-standard cooperative chart of accounts with real-time balances.",
    },
    "members": {
        "bir_module": "Subsidiary Ledger (Members' Equity)",
        "description": (
            "Member master file per CDA MC 2012-16, share capital, savings, "
            "and loan subsidiary ledger with automatic journal integration."
        ),
    },
    "reports": {
        "bir_module": "Financial Statements / Books of Accounts",
        "description": "CDA financial reports and BIR Books of Accounts with PDF export.",
    },
    "bir_cas": {
        "bir_module": "Systems Documentation",
        "description": "Mandatory BIR CAS technical requirements per RMC 5-2021 with PDF export.",
    },
    "admin_users": {
        "bir_module": "System Controls / Security",
        "description": "Role-based user accounts (Admin, Staff, Member) and access management.",
    },
}

BIR_EXTRA_MODULES = [
    {
        "name": "CDA Financial Reports",
        "description": "Statement of Financial Condition and Statement of Operations per CDA MC 2022-24.",
        "route": "/reports/cda",
        "bir_module": "Financial Statements (CDA)",
    },
    {
        "name": "About / User Manual",
        "description": "In-application procedural help for cooperative staff.",
        "route": "/about/user-manual",
        "bir_module": "End-User Documentation",
    },
]
