"""User manual content for CoopBooks."""

from app.bir_cas_config import SYSTEM_NAME, SYSTEM_VERSION
from app.config import USER_ROLES, can_post_entries, is_admin_role
from app.member_service import TXN_TYPE_LABELS


def user_manual_context():
    return {
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "sections": _manual_sections(),
        "roles": _role_guide(),
        "txn_types": [
            {"code": code, "label": label}
            for code, label in TXN_TYPE_LABELS.items()
        ],
    }


def _role_guide():
    guides = []
    for role in USER_ROLES:
        guides.append({
            "role": role,
            "can_post": can_post_entries(role),
            "is_admin": is_admin_role(role),
            "summary": _role_summary(role),
        })
    return guides


def _role_summary(role):
    if is_admin_role(role):
        return "Full access — post transactions, manage users, view all documentation."
    if can_post_entries(role):
        return "Operational access — post journal entries and member transactions."
    return "Read-only — view dashboard, accounts, members, and reports."


def _manual_sections():
    return [
        {
            "id": "introduction",
            "title": "1. Introduction",
            "icon": "bi-info-circle",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        f"{SYSTEM_NAME} is a cooperative accounting system built for Philippine "
                        "cooperatives. It supports double-entry bookkeeping using the CDA standard "
                        "chart of accounts, member share capital and savings tracking, financial "
                        "reporting, and BIR CAS registration documentation."
                    ),
                },
                {
                    "type": "list",
                    "title": "Key capabilities",
                    "entries": [
                        "Double-entry general journal with automatic balance validation",
                        "Member registry with share capital, savings, and loan ledgers",
                        "CDA-compliant Statement of Financial Condition and Operations",
                        "BIR Books of Accounts (General Journal, Ledger, Trial Balance)",
                        "Role-based access control with audit trail logging",
                    ],
                },
            ],
        },
        {
            "id": "getting-started",
            "title": "2. Getting Started",
            "icon": "bi-door-open",
            "content": [
                {
                    "type": "steps",
                    "title": "Logging in",
                    "entries": [
                        "Open the application home page and click the module you need, or go directly to /login.",
                        "Enter your username and password assigned by the cooperative administrator.",
                        "After a successful login you are redirected to the Dashboard.",
                        "Use Logout in the sidebar when you finish your session.",
                    ],
                },
                {
                    "type": "note",
                    "text": (
                        "Inactive accounts cannot log in. Contact an Admin if you see an "
                        "'Account is inactive' message."
                    ),
                },
            ],
        },
        {
            "id": "dashboard",
            "title": "3. Dashboard",
            "icon": "bi-speedometer2",
            "route": "/dashboard",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "The Dashboard gives a financial snapshot of the cooperative: active members, "
                        "share capital, savings deposits, cash, loans receivable, and journal activity."
                    ),
                },
                {
                    "type": "list",
                    "title": "Dashboard widgets",
                    "entries": [
                        "Stat cards — tap any card to jump to the related module",
                        "Trend chart — monthly cash inflow, savings, loan releases, and revenue",
                        "Columnar summary — period-over-period activity indicators",
                        "Recent journals — latest posted journal entries",
                    ],
                },
            ],
        },
        {
            "id": "journal",
            "title": "4. General Journal",
            "icon": "bi-journal-text",
            "route": "/journal",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "The General Journal records all double-entry transactions. Each entry must "
                        "have equal total debits and credits before it can be posted."
                    ),
                },
                {
                    "type": "steps",
                    "title": "Posting a new journal entry (Admin/Staff)",
                    "entries": [
                        "Go to General Journal and click New Entry.",
                        "Set the entry date, description, and optional reference.",
                        "Add one or more lines — select an account, enter debit or credit amounts.",
                        "Ensure total debits equal total credits.",
                        "Click Post Entry. The system assigns an entry number (JE-YYYY-NNN).",
                    ],
                },
                {
                    "type": "list",
                    "title": "Viewing entries",
                    "entries": [
                        "Click any entry in the list to view its detail and line items.",
                        "Each entry records who posted it and when.",
                    ],
                },
                {
                    "type": "note",
                    "text": "Member ledger transactions automatically create journal entries in the background.",
                },
            ],
        },
        {
            "id": "accounts",
            "title": "5. Chart of Accounts",
            "icon": "bi-list-columns",
            "route": "/accounts",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "The Chart of Accounts follows the CDA cooperative account structure. "
                        "Each account has a code, name, type (Asset, Liability, Equity, Revenue, Expense), "
                        "and normal balance (Debit or Credit)."
                    ),
                },
                {
                    "type": "list",
                    "title": "Filtering accounts",
                    "entries": [
                        "Browse all accounts from the sidebar link.",
                        "Filter by category or account code using URL parameters from dashboard links.",
                        "Current balance is computed from all posted journal lines.",
                    ],
                },
            ],
        },
        {
            "id": "members",
            "title": "6. Members & Member Ledger",
            "icon": "bi-people",
            "route": "/members",
            "content": [
                {
                    "type": "steps",
                    "title": "Adding a member (Admin/Staff)",
                    "entries": [
                        "Go to Members and click Add Member.",
                        "Fill in member number (auto-suggested), name, contact details, and membership date.",
                        "Enter opening share capital and savings balances if applicable.",
                        "Save — opening balances create ledger and journal entries automatically.",
                    ],
                },
                {
                    "type": "steps",
                    "title": "Recording member transactions",
                    "entries": [
                        "Open a member's profile and click View Ledger.",
                        "Click Add Transaction, choose the transaction type, date, and amount.",
                        "Add an optional reference and description.",
                        "Post — the system updates member balances and creates journal entries.",
                    ],
                },
                {
                    "type": "table_ref",
                    "title": "Transaction types",
                    "ref": "txn_types",
                },
            ],
        },
        {
            "id": "reports",
            "title": "7. Reports",
            "icon": "bi-file-earmark-bar-graph",
            "route": "/reports",
            "content": [
                {
                    "type": "list",
                    "title": "CDA financial reports",
                    "entries": [
                        "Statement of Financial Condition (Annex A) — assets, liabilities, equity",
                        "Statement of Operations (Annex B) — revenue, expenses, net surplus",
                        "Trial Balance — verify debits equal credits",
                    ],
                },
                {
                    "type": "list",
                    "title": "BIR Books of Accounts",
                    "entries": [
                        "General Journal — complete list of posted entries",
                        "General Ledger — per-account ledger with running balances",
                        "Member Subsidiary Ledger — share and savings detail by member",
                        "All books support PDF export for BIR CAS submission",
                    ],
                },
            ],
        },
        {
            "id": "documentation",
            "title": "8. BIR CAS Documentation",
            "icon": "bi-folder2-open",
            "route": "/documentation",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "The BIR CAS Docs menu contains mandatory technical requirements for "
                        "Computerized Accounting System registration under RMC No. 5-2021."
                    ),
                },
                {
                    "type": "list",
                    "entries": [
                        "System Description, Process Flows, System Modules",
                        "Sample Layouts with live report previews",
                        "System Controls and printable Audit Trail",
                        "Disaster Recovery Plan",
                        "Each section can be downloaded as PDF for RDO submission",
                    ],
                },
            ],
        },
        {
            "id": "administration",
            "title": "9. Administration",
            "icon": "bi-gear",
            "route": "/admin/users",
            "content": [
                {
                    "type": "paragraph",
                    "text": "Admin Options are visible only to users with the Admin role.",
                },
                {
                    "type": "steps",
                    "title": "Managing users",
                    "entries": [
                        "Go to Admin Options → User Management.",
                        "Add users with username, full name, email, role, and password.",
                        "Edit existing users — update role or status (Active/Inactive).",
                        "Delete users — at least one user must remain; you cannot delete yourself.",
                    ],
                },
                {
                    "type": "note",
                    "text": "All user create, update, and delete actions are recorded in the audit trail.",
                },
            ],
        },
        {
            "id": "troubleshooting",
            "title": "10. Tips & Troubleshooting",
            "icon": "bi-question-circle",
            "content": [
                {
                    "type": "list",
                    "title": "Common issues",
                    "entries": [
                        "Debits must equal credits — review all journal lines before posting.",
                        "Cannot post transactions — your role may be Member (read-only). Contact Admin.",
                        "Trial balance out of balance — check for incomplete or manual journal entries.",
                        "Session expired — log in again; your last page may be restored via the next parameter.",
                    ],
                },
                {
                    "type": "list",
                    "title": "Best practices",
                    "entries": [
                        "Post member transactions through the Member Ledger for automatic journal integration.",
                        "Run Trial Balance before generating CDA reports each period.",
                        "Export and archive audit trail PDFs regularly for BIR compliance.",
                        "Assign Staff role to bookkeepers; reserve Admin for supervisors only.",
                    ],
                },
            ],
        },
    ]
