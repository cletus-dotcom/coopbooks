"""Migration import templates — column definitions aligned with tenant database tables."""

MIGRATION_TABLES = [
    {
        "key": "cooperatives",
        "label": "Cooperative Profile",
        "filename": "01_cooperatives.xlsx",
        "sheet": "cooperatives",
        "order": 1,
        "description": "One row — cooperative profile stored in the tenant database.",
        "headers": [
            "name", "registration_no", "tin", "rdo", "coop_type",
            "address", "fiscal_year_end",
        ],
        "required": ["name"],
        "example": [
            "Sample Primary Multi-Purpose Cooperative", "CDA-XXXX-XXXXX",
            "123-456-789-000", "RDO 39", "Primary Multi-Purpose Cooperative",
            "Manila, Philippines", "December 31",
        ],
    },
    {
        "key": "accounts",
        "label": "Chart of Accounts",
        "filename": "02_accounts.xlsx",
        "sheet": "accounts",
        "order": 2,
        "description": "CDA chart of accounts. account_type: Asset, Liability, Equity, Revenue, Expense.",
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
        "description": "Login users. role: Admin, Staff, Member. password is hashed on import.",
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
        "description": "Member registry. membership_date format: YYYY-MM-DD. status: Active or Inactive.",
        "headers": [
            "member_no", "full_name", "email", "phone", "address",
            "membership_date", "share_capital", "savings_balance", "status",
        ],
        "required": ["member_no", "full_name"],
        "example": [
            "M-001", "Maria Santos", "maria@email.com", "09171234567",
            "Quezon City", "2024-01-15", "5000", "2500", "Active",
        ],
    },
    {
        "key": "journal_entries",
        "label": "Journal Entries",
        "filename": "05_journal_entries.xlsx",
        "sheet": "journal_entries",
        "order": 5,
        "description": "General journal headers. entry_date format: YYYY-MM-DD.",
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
        "description": "Journal detail lines. Use entry_no and account_code (not database IDs).",
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
        "description": (
            "Member subsidiary transactions. txn_type examples: SHARE_SUBSCRIPTION, "
            "SAVINGS_DEPOSIT, LOAN_RELEASE. ledger_type: share, savings, loan."
        ),
        "headers": [
            "member_no", "txn_date", "txn_type", "ledger_type",
            "reference", "description", "debit", "credit", "posted_by",
        ],
        "required": ["member_no", "txn_date", "txn_type", "ledger_type"],
        "example": [
            "M-001", "2025-01-20", "SAVINGS_DEPOSIT", "savings",
            "OR-2001", "Monthly savings", "0", "500", "Staff",
        ],
    },
]

MIGRATION_TABLE_MAP = {t["key"]: t for t in MIGRATION_TABLES}

IMPORT_ORDER = sorted(MIGRATION_TABLES, key=lambda t: t["order"])
