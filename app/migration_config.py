"""Migration import templates — columns aligned with PostgreSQL tables in this installation."""

from app.member_registry_config import (
    CIVIL_STATUSES,
    EDUCATION_LEVELS,
    GENDERS,
    MEMBER_STATUSES,
    MEMBERSHIP_TYPES,
)

# Maps template keys to physical tables (single shared database).
MIGRATION_DB_TABLES = {
    "cooperatives": "cooperatives",
    "accounts": "accounts",
    "users": "users",
    "members": "members",
    "journal_entries": "journal_entries",
    "journal_lines": "journal_lines",
    "member_ledger": "member_ledger",
}

ACCOUNT_TYPES = ("Asset", "Liability", "Equity", "Revenue", "Expense")
NORMAL_BALANCES = ("Debit", "Credit")
LEDGER_TYPES = ("share", "savings", "loan")
USER_ROLES_IMPORT = ("PlatformAdmin", "Admin", "Staff", "Member")
USER_STATUSES = ("Active", "Inactive")

MIGRATION_TABLES = [
    {
        "key": "cooperatives",
        "label": "Cooperative Profile",
        "filename": "01_cooperatives.xlsx",
        "sheet": "cooperatives",
        "order": 1,
        "db_table": "cooperatives",
        "description": (
            "One row — cooperative profile (cooperatives table). Also updates coop_registry "
            "for this installation (including contact_email). created_at is set automatically."
        ),
        "headers": [
            "name", "registration_no", "tin", "rdo", "coop_type",
            "address", "fiscal_year_end", "contact_email",
        ],
        "required": ["name"],
        "example": [
            "Sample Primary Multi-Purpose Cooperative", "CDA-XXXX-XXXXX",
            "123-456-789-000", "RDO 39", "Primary Multi-Purpose Cooperative",
            "Manila, Philippines", "December 31", "info@samplecoop.local",
        ],
    },
    {
        "key": "accounts",
        "label": "Chart of Accounts",
        "filename": "02_accounts.xlsx",
        "sheet": "accounts",
        "order": 2,
        "db_table": "accounts",
        "description": (
            "CDA chart of accounts. account_type: Asset, Liability, Equity, Revenue, Expense. "
            "normal_balance: Debit or Credit. is_active: TRUE/FALSE."
        ),
        "headers": [
            "code", "name", "account_type", "category", "normal_balance", "is_active",
        ],
        "required": ["code", "name", "account_type", "normal_balance"],
        "example": [
            "10101", "Cash on Hand", "Asset", "Cash and Cash Equivalents", "Debit", "TRUE",
        ],
    },
    {
        "key": "users",
        "label": "System Users",
        "filename": "03_users.xlsx",
        "sheet": "users",
        "order": 3,
        "db_table": "users",
        "description": (
            "Login users (users table). role: PlatformAdmin, Admin, Staff, or Member. "
            "password is hashed on import (stored as password_hash). "
            "PlatformAdmin accounts are never deleted by replace mode."
        ),
        "headers": [
            "username", "full_name", "email", "role", "status", "password",
        ],
        "required": ["username", "password"],
        "example": [
            "bookkeeper1", "Juan Dela Cruz", "juan@coop.local", "Staff", "Active", "ChangeMe123",
        ],
    },
    {
        "key": "members",
        "label": "Members",
        "filename": "04_members.xlsx",
        "sheet": "members",
        "order": 4,
        "db_table": "members",
        "description": (
            "CDA MC 2012-16 membership registry (members table). "
            "membership_date = date accepted (I-a). "
            "initial_paid_up_capital sets share_capital on import; optional savings_balance "
            "creates opening member ledger entries. full_name is computed from name parts. "
            "Dates: YYYY-MM-DD. status: Active, Inactive, or Terminated."
        ),
        "valid_values": {
            "membership_type": MEMBERSHIP_TYPES,
            "gender": GENDERS,
            "civil_status": CIVIL_STATUSES,
            "highest_education": EDUCATION_LEVELS,
            "status": MEMBER_STATUSES,
        },
        "headers": [
            "member_no", "last_name", "first_name", "middle_name", "tin",
            "membership_date", "bod_acceptance_resolution", "membership_type",
            "initial_shares", "initial_subscription_amount", "initial_paid_up_capital",
            "address", "birth_date", "gender", "civil_status", "highest_education",
            "occupation_income_source", "number_of_dependents",
            "religion_social_affiliation", "annual_income",
            "register_entry_date", "email", "phone", "savings_balance", "status",
            "termination_date", "termination_bod_resolution",
        ],
        "required": ["member_no", "last_name", "first_name", "tin", "membership_date"],
        "example": [
            "M-001", "Santos", "Maria", "L.", "123-456-789-000",
            "2024-01-15", "BOD-2024-01", "Regular",
            "50", "5000", "5000",
            "123 Main St, Quezon City", "1990-05-20", "Female", "Single", "College",
            "Teacher", "2", "Roman Catholic", "360000",
            "2024-01-15", "maria@email.com", "09171234567", "2500", "Active",
            "", "",
        ],
    },
    {
        "key": "journal_entries",
        "label": "Journal Entries",
        "filename": "05_journal_entries.xlsx",
        "sheet": "journal_entries",
        "order": 5,
        "db_table": "journal_entries",
        "description": "General journal headers (journal_entries). entry_date: YYYY-MM-DD.",
        "headers": [
            "entry_no", "entry_date", "description", "reference", "posted_by",
        ],
        "required": ["entry_no", "entry_date"],
        "example": [
            "JE-2025-001", "2025-01-15", "Opening share capital", "OR-1001", "Admin",
        ],
    },
    {
        "key": "journal_lines",
        "label": "Journal Lines",
        "filename": "06_journal_lines.xlsx",
        "sheet": "journal_lines",
        "order": 6,
        "db_table": "journal_lines",
        "description": (
            "Journal detail lines (journal_lines). Resolves entry_no → entry_id and "
            "account_code → account_id. debit/credit are numeric."
        ),
        "headers": [
            "entry_no", "account_code", "debit", "credit", "memo",
        ],
        "required": ["entry_no", "account_code"],
        "example": [
            "JE-2025-001", "10101", "12000", "0", "Share capital collection",
        ],
    },
    {
        "key": "member_ledger",
        "label": "Member Ledger",
        "filename": "07_member_ledger.xlsx",
        "sheet": "member_ledger",
        "order": 7,
        "db_table": "member_ledger",
        "description": (
            "Member subsidiary ledger (member_ledger). txn_type examples: SHARE_SUBSCRIPTION, "
            "SAVINGS_DEPOSIT, LOAN_RELEASE. ledger_type: share, savings, or loan. "
            "Optional entry_no links journal_entry_id."
        ),
        "headers": [
            "member_no", "txn_date", "txn_type", "ledger_type",
            "reference", "description", "entry_no", "debit", "credit", "posted_by",
        ],
        "required": ["member_no", "txn_date", "txn_type", "ledger_type"],
        "example": [
            "M-001", "2025-01-20", "SAVINGS_DEPOSIT", "savings",
            "OR-2001", "Monthly savings", "", "0", "500", "Staff",
        ],
    },
]

MIGRATION_TABLE_MAP = {t["key"]: t for t in MIGRATION_TABLES}

IMPORT_ORDER = sorted(MIGRATION_TABLES, key=lambda t: t["order"])
