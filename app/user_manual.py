"""User manual content for CoopBooks — aligned with routes, sidebar, and roles."""

from app.bir_cas_config import SYSTEM_NAME, SYSTEM_VERSION
from app.config import USER_ROLES, can_post_entries, is_admin_role
from app.member_service import POSTABLE_TXN_TYPES, TXN_TYPE_LABELS


def user_manual_context():
    return {
        "system_name": SYSTEM_NAME,
        "system_version": SYSTEM_VERSION,
        "sections": _manual_sections(),
        "roles": _role_guide(),
        "txn_types": [
            {"code": code, "label": TXN_TYPE_LABELS[code]}
            for code in POSTABLE_TXN_TYPES
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
        return (
            "Cooperative administration — manage users (add/edit/deactivate) and full operational "
            "access to journal, members, and reports."
        )
    if can_post_entries(role):
        return "Operational access — post general journal entries and member ledger transactions."
    return "Read-only — view dashboard, chart of accounts, members, and reports."


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
                        f"{SYSTEM_NAME} is a single-cooperative accounting application for "
                        "Philippine cooperatives. Each installation serves one registered "
                        "cooperative with a shared PostgreSQL database for the chart of accounts, "
                        "membership registry, general journal, and reports."
                    ),
                },
                {
                    "type": "list",
                    "title": "Key capabilities",
                    "entries": [
                        "Double-entry general journal with debit/credit balance validation",
                        "CDA MC 2012-16 membership registry and member subsidiary ledgers",
                        "CDA MC 2022-24 chart of accounts and financial reports (Annex A & B)",
                        "BIR Books of Accounts with PDF export (General Journal, Ledger, Trial Balance)",
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
                        "Open the home page (/) and choose a module, or go to /login.",
                        "Enter the username and password assigned by your cooperative administrator.",
                        "There is no separate coop code on login — one cooperative is configured per installation.",
                        "After login you are redirected to the Dashboard (or the page you requested via ?next=).",
                        "Use Logout at the bottom of the sidebar when you finish.",
                    ],
                },
                {
                    "type": "list",
                    "title": "Sidebar navigation",
                    "entries": [
                        "Accounting — Dashboard, General Journal, Chart of Accounts, Members",
                        "Reports — CDA Reports and BIR Books of Accounts (expand Reports in the sidebar)",
                        "About — User Manual (this guide)",
                        "Administration — Admin Options → User Management (Admin role only)",
                    ],
                },
                {
                    "type": "note",
                    "text": (
                        "Inactive user accounts cannot log in. Contact an Admin if you see "
                        "'Account is inactive.'"
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
                        "The Dashboard summarizes cooperative activity: active members, share capital, "
                        "savings, cash, loans receivable, and recent journal entries."
                    ),
                },
                {
                    "type": "list",
                    "title": "Overview sections",
                    "entries": [
                        "Stat cards — tap a card to open Members, Accounts, or related views",
                        "Trends — monthly cash inflow, savings, loan releases, and revenue (loaded after stats)",
                        "Columnar summary — period activity indicators",
                        "Recent journals — latest posted entries with links to detail",
                        "New Entry — shortcut to post a general journal entry (Admin or Staff)",
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
                        "The General Journal (/journal) is the cooperative's double-entry book. "
                        "Each entry must have equal total debits and credits before posting."
                    ),
                },
                {
                    "type": "steps",
                    "title": "Posting a new entry (Admin or Staff)",
                    "entries": [
                        "Go to General Journal and click New Entry (/journal/new).",
                        "Set the entry date, description, and optional reference.",
                        "Add lines — select an account code and enter debit or credit amounts.",
                        "Ensure total debits equal total credits; the Post Entry button enables when balanced.",
                        "Click Post Entry. The system assigns an entry number (JE-YYYY-NNN).",
                    ],
                },
                {
                    "type": "list",
                    "title": "Viewing entries",
                    "entries": [
                        "Click any entry in the list to open its detail page (/journal/<entry_no>).",
                        "Each entry records who posted it and when.",
                    ],
                },
                {
                    "type": "note",
                    "text": (
                        "Member ledger transactions are recorded separately in the member subsidiary "
                        "ledger. Post corresponding general journal entries when you need books "
                        "integration — the two ledgers are not auto-linked on every member transaction."
                    ),
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
                        "The Chart of Accounts (/accounts) follows the CDA cooperative account "
                        "structure. Each account has a code, name, type (Asset, Liability, Equity, "
                        "Revenue, Expense), category, and normal balance (Debit or Credit)."
                    ),
                },
                {
                    "type": "list",
                    "title": "Using the chart",
                    "entries": [
                        "Browse all accounts from the sidebar.",
                        "Filter by category or account code using dashboard links or URL parameters.",
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
                    "type": "paragraph",
                    "text": (
                        "The Members page (/members) is the cooperative membership registry per "
                        "CDA MC 2012-16. Expand a member row (or card on mobile) to view registry "
                        "details, or open the full transaction ledger for a member."
                    ),
                },
                {
                    "type": "steps",
                    "title": "Adding a member (Admin or Staff)",
                    "entries": [
                        "Go to Members and click Add Member.",
                        "Complete registry sections A–C (name, membership number, TIN), "
                        "Section I (acceptance date, BOD resolution, membership type, initial share subscription), "
                        "and Section II (profile fields such as address, birth date, occupation, and income).",
                        "Enter initial paid-up capital and optional opening savings balance.",
                        "Save — opening balances create member ledger entries and update share/savings totals on the member record.",
                    ],
                },
                {
                    "type": "steps",
                    "title": "Recording member transactions",
                    "entries": [
                        "From Members, expand the member and click View Full Ledger (or View All on mobile).",
                        "On the member ledger page (/members/<member_no>/ledger), click Record Transaction.",
                        "Choose transaction type, date, and amount; add optional reference and description.",
                        "Post — balances on the member record and subsidiary ledger update immediately.",
                    ],
                },
                {
                    "type": "table_ref",
                    "title": "Postable transaction types",
                    "ref": "txn_types",
                },
            ],
        },
        {
            "id": "reports",
            "title": "7. Reports",
            "icon": "bi-file-earmark-bar-graph",
            "route": "/reports/cda",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "Open Reports in the sidebar, then choose CDA Reports or BIR Books of Accounts. "
                        "The default /reports path opens CDA Reports."
                    ),
                },
                {
                    "type": "list",
                    "title": "CDA Reports (/reports/cda)",
                    "entries": [
                        "Annex A — Statement of Financial Condition (/reports/sfc)",
                        "Annex B — Statement of Operations (/reports/operations)",
                        "Links to official CDA report form downloads",
                    ],
                },
                {
                    "type": "list",
                    "title": "BIR Books of Accounts (/reports/bir-books)",
                    "entries": [
                        "General Journal — all posted entries (/reports/general-journal)",
                        "General Ledger — per-account with running balances (/reports/general-ledger)",
                        "Trial Balance — verify debits equal credits (/reports/trial-balance)",
                        "Member Subsidiary Ledger — share and savings detail by member (/reports/member-subsidiary)",
                        "PDF export available from BIR book pages",
                    ],
                },
            ],
        },
        {
            "id": "administration",
            "title": "8. Administration",
            "icon": "bi-gear",
            "route": "/admin/users",
            "content": [
                {
                    "type": "paragraph",
                    "text": (
                        "User management is available to Admin users under Admin Options → "
                        "User Management (/admin/users). Staff and Member roles do not see this menu."
                    ),
                },
                {
                    "type": "steps",
                    "title": "Managing users",
                    "entries": [
                        "Go to Admin Options → User Management.",
                        "Add users with username, full name, email, role, and password.",
                        "Roles available: Admin, Staff, or Member.",
                        "Edit users — update role or status (Active/Inactive).",
                        "Delete users — at least one user must remain; you cannot delete yourself.",
                    ],
                },
                {
                    "type": "note",
                    "text": "User create, update, and delete actions are recorded in the audit trail.",
                },
            ],
        },
        {
            "id": "troubleshooting",
            "title": "9. Tips & Troubleshooting",
            "icon": "bi-question-circle",
            "content": [
                {
                    "type": "list",
                    "title": "Common issues",
                    "entries": [
                        "Debits must equal credits — review all journal lines before posting.",
                        "Cannot post transactions — your role may be Member (read-only). Contact Admin.",
                        "Trial balance out of balance — check for unposted or unbalanced journal entries.",
                        "Session expired — log in again; ?next= may restore your intended page.",
                    ],
                },
                {
                    "type": "list",
                    "title": "Best practices",
                    "entries": [
                        "Keep the membership registry complete per CDA MC 2012-16 before accepting new members.",
                        "Record member share and savings activity through the member ledger; post matching general journal entries for book integration.",
                        "Run Trial Balance before generating CDA reports each period.",
                        "Assign Staff role to bookkeepers; reserve Admin for supervisors.",
                    ],
                },
            ],
        },
    ]
