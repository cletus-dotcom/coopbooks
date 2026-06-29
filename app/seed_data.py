"""CDA MC 2022-24 Revised Standard Chart of Accounts (representative subset)."""

CDA_CHART_OF_ACCOUNTS = [
    ("10101", "Cash on Hand", "Asset", "Cash and Cash Equivalents", "Debit"),
    ("10103", "Cash in Bank", "Asset", "Cash and Cash Equivalents", "Debit"),
    ("10104", "Cash in Cooperative Federation", "Asset", "Cash and Cash Equivalents", "Debit"),
    ("10105", "Petty Cash Fund", "Asset", "Cash and Cash Equivalents", "Debit"),
    ("11101", "Loans Receivable – Current", "Asset", "Loans and Receivables", "Debit"),
    ("11105", "Allowance for Probable Losses on Loans", "Asset", "Loans and Receivables", "Credit"),
    ("12101", "Saving Deposits (Contra)", "Asset", "Deposit Liabilities Control", "Debit"),
    ("13101", "Merchandise Inventory", "Asset", "Inventories", "Debit"),
    ("14101", "Land", "Asset", "Property, Plant and Equipment", "Debit"),
    ("14102", "Building", "Asset", "Property, Plant and Equipment", "Debit"),
    ("14103", "Accumulated Depreciation – Building", "Asset", "Property, Plant and Equipment", "Credit"),
    ("14104", "Furniture, Fixtures & Equipment", "Asset", "Property, Plant and Equipment", "Debit"),
    ("20101", "Saving Deposits", "Liability", "Deposit Liabilities", "Credit"),
    ("20102", "Time Deposits", "Liability", "Deposit Liabilities", "Credit"),
    ("21101", "Accounts Payable – Trade", "Liability", "Trade and Other Payables", "Credit"),
    ("22101", "SSS/Pag-Ibig Premium Contributions Payable", "Liability", "Accrued Expenses", "Credit"),
    ("23101", "Interest on Share Capital Payable", "Liability", "Other Current Liabilities", "Credit"),
    ("23102", "Patronage Refund Payable", "Liability", "Other Current Liabilities", "Credit"),
    ("23103", "Due to Union/Federation (CETF)", "Liability", "Other Current Liabilities", "Credit"),
    ("24101", "Loans Payable", "Liability", "Non-Current Liabilities", "Credit"),
    ("30101", "Paid-up Share Capital – Common", "Equity", "Members' Equity", "Credit"),
    ("30102", "Paid-up Share Capital – Preferred", "Equity", "Members' Equity", "Credit"),
    ("30201", "Undivided Net Surplus", "Equity", "Members' Equity", "Credit"),
    ("30301", "Reserve Fund", "Equity", "Statutory Funds", "Credit"),
    ("30302", "Coop. Education & Training Fund", "Equity", "Statutory Funds", "Credit"),
    ("30303", "Community Development Fund", "Equity", "Statutory Funds", "Credit"),
    ("30304", "Optional Fund", "Equity", "Statutory Funds", "Credit"),
    ("40101", "Interest Income from Loans", "Revenue", "Income from Credit Operations", "Credit"),
    ("40102", "Service Fees", "Revenue", "Income from Credit Operations", "Credit"),
    ("41101", "Sales", "Revenue", "Marketing Operations", "Credit"),
    ("42101", "Membership Fee", "Revenue", "Other Income", "Credit"),
    ("42102", "Miscellaneous Income", "Revenue", "Other Income", "Credit"),
    ("50101", "Interest Expense on Borrowings", "Expense", "Financing Costs", "Debit"),
    ("51101", "Salaries and Wages", "Expense", "Administrative Costs", "Debit"),
    ("51102", "SSS, Philhealth, ECC, Pag-ibig Premium", "Expense", "Administrative Costs", "Debit"),
    ("51103", "Office Supplies", "Expense", "Administrative Costs", "Debit"),
    ("51104", "Power, Light and Water", "Expense", "Administrative Costs", "Debit"),
    ("51105", "Depreciation", "Expense", "Administrative Costs", "Debit"),
    ("51106", "Provision for Probable Losses on Loans", "Expense", "Administrative Costs", "Debit"),
]

SAMPLE_MEMBERS = [
    ("M-001", "Juan Dela Cruz", 5000, 2500),
    ("M-002", "Maria Santos", 10000, 8000),
    ("M-003", "Pedro Reyes", 2500, 1200),
    ("M-004", "Ana Garcia", 7500, 4500),
    ("M-005", "Luis Mendoza", 3000, 600),
]

SAMPLE_JOURNALS = [
    {
        "entry_no": "JE-2025-010",
        "months_ago": 5,
        "description": "Opening share capital – Q3 collections",
        "reference": "OR batch Q3",
        "lines": [
            ("10101", 12000, 0, "Share capital collection"),
            ("30101", 0, 12000, "Paid-up share capital"),
        ],
    },
    {
        "entry_no": "JE-2025-011",
        "months_ago": 4,
        "description": "Member savings – October deposits",
        "reference": "Deposit slips Oct",
        "lines": [
            ("10103", 9500, 0, "Savings deposits received"),
            ("20101", 0, 9500, "Saving deposits liability"),
        ],
    },
    {
        "entry_no": "JE-2025-012",
        "months_ago": 3,
        "description": "Loan releases – November cycle",
        "reference": "Loan voucher batch",
        "lines": [
            ("11101", 15000, 0, "New loans disbursed"),
            ("10103", 0, 15000, "Cash disbursement"),
        ],
    },
    {
        "entry_no": "JE-2026-001",
        "months_ago": 2,
        "description": "Additional share capital subscriptions",
        "reference": "CDA MC 2022-24",
        "lines": [
            ("10101", 10500, 0, "Member share capital collection"),
            ("30101", 0, 10500, "Paid-up share capital"),
        ],
    },
    {
        "entry_no": "JE-2026-002",
        "months_ago": 1,
        "description": "Member savings deposits – January",
        "reference": "Deposit slip batch",
        "lines": [
            ("10103", 7300, 0, "Savings deposits received"),
            ("20101", 0, 7300, "Saving deposits liability"),
        ],
    },
    {
        "entry_no": "JE-2026-003",
        "months_ago": 0,
        "description": "Loan interest income for the month",
        "reference": "Billing run Jan 2026",
        "lines": [
            ("10103", 8500, 0, "Interest collections"),
            ("40101", 0, 8500, "Interest income from loans"),
        ],
    },
]
