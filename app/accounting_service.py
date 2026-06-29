"""Dashboard metric definitions and financial aggregations."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.models import Account, JournalEntry, JournalLine, Member, local_time

CASH_CODES = ("10101", "10103", "10104", "10105")
SAVINGS_CODES = ("20101", "20102")
SHARE_CODES = ("30101", "30102")
LOAN_CODES = ("11101",)
REVENUE_CODES = ("40101", "40102", "41101", "42101", "42102")

DASHBOARD_CARDS = [
    {
        "id": "members",
        "label": "Active Members",
        "stat_key": "total_members",
        "format": "count",
        "icon": "bi-people",
        "url": "/members",
        "detail": "Member registry & status",
    },
    {
        "id": "share_capital",
        "label": "Share Capital",
        "stat_key": "total_share_capital",
        "format": "currency",
        "icon": "bi-pie-chart",
        "url": "/members?focus=share",
        "detail": "Paid-up share capital by member",
    },
    {
        "id": "savings",
        "label": "Savings Deposits",
        "stat_key": "total_savings",
        "format": "currency",
        "icon": "bi-piggy-bank",
        "url": "/members?focus=savings",
        "detail": "Member savings balances",
    },
    {
        "id": "cash",
        "label": "Cash & Equivalents",
        "stat_key": "total_cash",
        "format": "currency",
        "icon": "bi-cash-stack",
        "url": "/accounts?category=Cash and Cash Equivalents",
        "detail": "CDA cash account balances",
    },
    {
        "id": "loans",
        "label": "Loans Receivable",
        "stat_key": "total_loans_receivable",
        "format": "currency",
        "icon": "bi-bank",
        "url": "/accounts?code=11101",
        "detail": "Loans receivable – current",
    },
    {
        "id": "journals",
        "label": "Journal Entries",
        "stat_key": "journal_count",
        "format": "count",
        "icon": "bi-journal-text",
        "url": "/journal",
        "detail": "General journal transactions",
    },
]

TREND_DATASETS = [
    {"key": "cash_inflow", "label": "Cash Inflow", "codes": CASH_CODES, "field": "debit", "color": "#1565C0"},
    {"key": "savings", "label": "Savings Deposits", "codes": SAVINGS_CODES, "field": "credit", "color": "#2E7D32"},
    {"key": "loan_activity", "label": "Loan Releases", "codes": LOAN_CODES, "field": "debit", "color": "#EF6C00"},
    {"key": "revenue", "label": "Revenue", "codes": REVENUE_CODES, "field": "credit", "color": "#7B1FA2"},
]


def _decimal(value):
    return Decimal(str(value or 0))


def _month_start(year, month):
    return date(year, month, 1)


def _next_month_start(year, month):
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _recent_month_starts(months=6):
    today = local_time().date()
    year, month = today.year, today.month
    starts = []
    for offset in range(months - 1, -1, -1):
        m = month - offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        starts.append(_month_start(y, m))
    return starts


def account_balance(account_id):
    totals = db.session.query(
        func.coalesce(func.sum(JournalLine.debit), 0),
        func.coalesce(func.sum(JournalLine.credit), 0),
    ).filter(JournalLine.account_id == account_id).one()

    account = Account.query.get(account_id)
    debit_total = _decimal(totals[0])
    credit_total = _decimal(totals[1])

    if account.normal_balance == "Debit":
        return debit_total - credit_total
    return credit_total - debit_total


def _balance_for_codes(codes):
    accounts = Account.query.filter(Account.code.in_(codes)).all()
    return sum(account_balance(a.id) for a in accounts)


def _sum_lines_in_period(account_codes, period_start, period_end, field):
    column = JournalLine.debit if field == "debit" else JournalLine.credit
    total = db.session.query(
        func.coalesce(func.sum(column), 0),
    ).join(JournalEntry).join(Account).filter(
        Account.code.in_(account_codes),
        JournalEntry.entry_date >= period_start,
        JournalEntry.entry_date < period_end,
    ).scalar()
    return float(total or 0)


def _journal_count_in_period(period_start, period_end):
    return JournalEntry.query.filter(
        JournalEntry.entry_date >= period_start,
        JournalEntry.entry_date < period_end,
    ).count()


def dashboard_stats():
    total_members = Member.query.filter_by(status="Active").count()
    total_share = db.session.query(
        func.coalesce(func.sum(Member.share_capital), 0)
    ).scalar()
    total_savings = db.session.query(
        func.coalesce(func.sum(Member.savings_balance), 0)
    ).scalar()
    journal_count = JournalEntry.query.count()
    total_cash = _balance_for_codes(CASH_CODES)
    total_loans = _balance_for_codes(LOAN_CODES)

    summary = {
        "total_members": total_members,
        "total_share_capital": float(total_share or 0),
        "total_savings": float(total_savings or 0),
        "journal_count": journal_count,
        "total_cash": float(total_cash),
        "total_loans_receivable": float(total_loans),
        "total_assets": float(_total_assets()),
    }

    cards = []
    for card in DASHBOARD_CARDS:
        cards.append({
            **card,
            "value": summary[card["stat_key"]],
        })

    return {"summary": summary, "cards": cards}


def dashboard_trends(months=6):
    month_starts = _recent_month_starts(months)
    labels = [start.strftime("%b %Y") for start in month_starts]

    datasets = []
    for spec in TREND_DATASETS:
        data = []
        for start in month_starts:
            end = _next_month_start(start.year, start.month)
            data.append(_sum_lines_in_period(spec["codes"], start, end, spec["field"]))
        datasets.append({
            "label": spec["label"],
            "data": data,
            "backgroundColor": spec["color"],
            "borderColor": spec["color"],
            "borderRadius": 6,
        })

    journal_counts = []
    for start in month_starts:
        end = _next_month_start(start.year, start.month)
        journal_counts.append(_journal_count_in_period(start, end))

    return {
        "labels": labels,
        "datasets": datasets,
        "journal_counts": journal_counts,
    }


def _total_assets():
    total = Decimal("0")
    for account in Account.query.filter_by(account_type="Asset", is_active=True):
        total += account_balance(account.id)
    return total


def _pct_of_assets(amount, total_assets):
    if not total_assets:
        return None
    return round(float(amount) / float(total_assets) * 100, 1)


def dashboard_columnar():
    stats = dashboard_stats()["summary"]
    total_assets = stats["total_assets"] or 1

    month_starts = _recent_month_starts(2)
    current_start = month_starts[-1]
    prior_start = month_starts[-2] if len(month_starts) > 1 else month_starts[-1]
    current_end = _next_month_start(current_start.year, current_start.month)
    prior_end = _next_month_start(prior_start.year, prior_start.month)

    current_journal_count = _journal_count_in_period(current_start, current_end)
    prior_journal_count = _journal_count_in_period(prior_start, prior_end)

    def activity_label(current, prior, suffix=""):
        if current > prior:
            return f"↑ vs prior month{suffix}"
        if current < prior:
            return f"↓ vs prior month{suffix}"
        return f"→ unchanged{suffix}"

    sections = [
        {
            "title": "Membership & Deposits",
            "icon": "bi-people",
            "rows": [
                {
                    "indicator": "Active Members",
                    "subtitle": "Registered cooperative members",
                    "amount": stats["total_members"],
                    "format": "count",
                    "pct": None,
                    "activity": f"{stats['total_members']} active",
                    "url": "/members",
                },
                {
                    "indicator": "Share Capital",
                    "subtitle": "Paid-up share capital (Account 30101)",
                    "amount": stats["total_share_capital"],
                    "format": "currency",
                    "pct": _pct_of_assets(stats["total_share_capital"], total_assets),
                    "activity": activity_label(
                        _sum_lines_in_period(SHARE_CODES, current_start, current_end, "credit"),
                        _sum_lines_in_period(SHARE_CODES, prior_start, prior_end, "credit"),
                    ),
                    "url": "/members?focus=share",
                },
                {
                    "indicator": "Savings Deposits",
                    "subtitle": "Member saving deposit liabilities",
                    "amount": stats["total_savings"],
                    "format": "currency",
                    "pct": _pct_of_assets(stats["total_savings"], total_assets),
                    "activity": activity_label(
                        _sum_lines_in_period(SAVINGS_CODES, current_start, current_end, "credit"),
                        _sum_lines_in_period(SAVINGS_CODES, prior_start, prior_end, "credit"),
                    ),
                    "url": "/members?focus=savings",
                },
            ],
        },
        {
            "title": "Assets & Operations",
            "icon": "bi-bar-chart",
            "rows": [
                {
                    "indicator": "Cash & Equivalents",
                    "subtitle": "Accounts 10101–10105 per CDA chart",
                    "amount": stats["total_cash"],
                    "format": "currency",
                    "pct": _pct_of_assets(stats["total_cash"], total_assets),
                    "activity": activity_label(
                        _sum_lines_in_period(CASH_CODES, current_start, current_end, "debit"),
                        _sum_lines_in_period(CASH_CODES, prior_start, prior_end, "debit"),
                    ),
                    "url": "/accounts?category=Cash and Cash Equivalents",
                },
                {
                    "indicator": "Loans Receivable",
                    "subtitle": "Loans receivable – current (11101)",
                    "amount": stats["total_loans_receivable"],
                    "format": "currency",
                    "pct": _pct_of_assets(stats["total_loans_receivable"], total_assets),
                    "activity": activity_label(
                        _sum_lines_in_period(LOAN_CODES, current_start, current_end, "debit"),
                        _sum_lines_in_period(LOAN_CODES, prior_start, prior_end, "debit"),
                    ),
                    "url": "/accounts?code=11101",
                },
                {
                    "indicator": "Journal Entries",
                    "subtitle": "Posted transactions this period",
                    "amount": stats["journal_count"],
                    "format": "count",
                    "pct": None,
                    "activity": activity_label(current_journal_count, prior_journal_count, " posted"),
                    "url": "/journal",
                },
            ],
        },
    ]

    return {
        "sections": sections,
        "total_assets": stats["total_assets"],
        "period_label": current_start.strftime("%B %Y"),
        "prior_period_label": prior_start.strftime("%B %Y"),
    }


def trial_balance():
    rows = []
    for account in Account.query.filter_by(is_active=True).order_by(Account.code).all():
        balance = account_balance(account.id)
        if balance == 0:
            continue
        debit = float(balance) if account.normal_balance == "Debit" and balance > 0 else 0
        credit = float(balance) if account.normal_balance == "Credit" and balance > 0 else 0
        if account.normal_balance == "Debit" and balance < 0:
            credit = float(abs(balance))
        elif account.normal_balance == "Credit" and balance < 0:
            debit = float(abs(balance))
        rows.append({
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
            "debit": debit,
            "credit": credit,
        })
    return rows


def statement_of_financial_condition():
    sections = {
        "Asset": [],
        "Liability": [],
        "Equity": [],
    }
    totals = {"Asset": Decimal("0"), "Liability": Decimal("0"), "Equity": Decimal("0")}

    for account in Account.query.filter(
        Account.account_type.in_(("Asset", "Liability", "Equity")),
        Account.is_active.is_(True),
    ).order_by(Account.code):
        balance = account_balance(account.id)
        if balance == 0:
            continue
        sections[account.account_type].append({
            "code": account.code,
            "name": account.name,
            "category": account.category,
            "amount": float(balance),
        })
        totals[account.account_type] += balance

    return {
        "sections": sections,
        "total_assets": float(totals["Asset"]),
        "total_liabilities": float(totals["Liability"]),
        "total_equity": float(totals["Equity"]),
    }


def statement_of_operations():
    revenue_rows = []
    expense_rows = []
    total_revenue = Decimal("0")
    total_expense = Decimal("0")

    for account in Account.query.filter(
        Account.account_type.in_(("Revenue", "Expense")),
        Account.is_active.is_(True),
    ).order_by(Account.code):
        balance = account_balance(account.id)
        if balance == 0:
            continue
        row = {"code": account.code, "name": account.name, "amount": float(balance)}
        if account.account_type == "Revenue":
            revenue_rows.append(row)
            total_revenue += balance
        else:
            expense_rows.append(row)
            total_expense += balance

    net_surplus = total_revenue - total_expense
    return {
        "revenue": revenue_rows,
        "expenses": expense_rows,
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expense),
        "net_surplus": float(net_surplus),
    }


def recent_journal_entries(limit=10):
    entries = JournalEntry.query.order_by(JournalEntry.entry_date.desc()).limit(limit).all()
    result = []
    for entry in entries:
        total_debit = sum(_decimal(line.debit) for line in entry.lines)
        result.append({
            "entry_no": entry.entry_no,
            "entry_date": entry.entry_date.isoformat() if entry.entry_date else "",
            "description": entry.description or "",
            "reference": entry.reference or "",
            "posted_by": entry.posted_by or "",
            "total_debit": float(total_debit),
            "line_count": len(entry.lines),
        })
    return result


def serialize_journal_entry(entry):
    return {
        "entry_no": entry.entry_no,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else "",
        "description": entry.description or "",
        "reference": entry.reference or "",
        "posted_by": entry.posted_by or "",
        "lines": [{
            "code": line.account.code,
            "name": line.account.name,
            "debit": float(line.debit or 0),
            "credit": float(line.credit or 0),
            "memo": line.memo or "",
        } for line in entry.lines],
    }


def accounts_with_balances(filters=None):
    """Return active accounts with optional filters and computed balances."""
    query = Account.query.filter_by(is_active=True)
    filters = filters or {}

    if filters.get("code"):
        query = query.filter_by(code=filters["code"])
    if filters.get("category"):
        query = query.filter_by(category=filters["category"])
    if filters.get("account_type"):
        query = query.filter_by(account_type=filters["account_type"])

    rows = []
    for account in query.order_by(Account.code).all():
        balance = account_balance(account.id)
        rows.append({
            "account": account,
            "balance": float(balance),
        })
    return rows


def general_journal_book():
    """All journal entries formatted as a General Journal book."""
    entries = JournalEntry.query.order_by(
        JournalEntry.entry_date, JournalEntry.entry_no
    ).all()
    result = []
    for entry in entries:
        result.append({
            "entry_no": entry.entry_no,
            "entry_date": entry.entry_date.isoformat() if entry.entry_date else "",
            "description": entry.description or "",
            "reference": entry.reference or "",
            "posted_by": entry.posted_by or "",
            "lines": [{
                "code": line.account.code,
                "name": line.account.name,
                "debit": float(line.debit or 0),
                "credit": float(line.credit or 0),
                "memo": line.memo or "",
            } for line in entry.lines],
        })
    return result


def general_ledger_accounts(account_code=None):
    """Per-account ledger with running balance for General Ledger report."""
    query = Account.query.filter_by(is_active=True)
    if account_code:
        query = query.filter_by(code=account_code)
    accounts = query.order_by(Account.code).all()

    result = []
    for account in accounts:
        lines_q = (
            db.session.query(JournalLine, JournalEntry)
            .join(JournalEntry)
            .filter(JournalLine.account_id == account.id)
            .order_by(JournalEntry.entry_date, JournalEntry.entry_no)
        )
        running = Decimal("0")
        lines = []
        for jl, je in lines_q:
            debit = _decimal(jl.debit)
            credit = _decimal(jl.credit)
            if account.normal_balance == "Debit":
                running += debit - credit
            else:
                running += credit - debit
            lines.append({
                "entry_date": je.entry_date.isoformat() if je.entry_date else "",
                "entry_no": je.entry_no,
                "reference": je.reference or "",
                "description": je.description or "",
                "debit": float(debit),
                "credit": float(credit),
                "balance": float(running),
            })
        if lines:
            result.append({
                "code": account.code,
                "name": account.name,
                "account_type": account.account_type,
                "normal_balance": account.normal_balance,
                "lines": lines,
                "ending_balance": float(running),
            })
    return result


def member_subsidiary_ledger():
    """Member share/savings subsidiary ledger for BIR sample layouts."""
    from app.models import MemberLedger

    members = Member.query.order_by(Member.member_no).all()
    result = []
    for member in members:
        entries = (
            MemberLedger.query
            .filter_by(member_id=member.id)
            .order_by(MemberLedger.txn_date, MemberLedger.id)
            .all()
        )
        if not entries:
            continue
        share_bal = savings_bal = Decimal("0")
        lines = []
        for e in entries:
            debit = _decimal(e.debit)
            credit = _decimal(e.credit)
            if e.ledger_type == "share":
                share_bal += credit - debit
            elif e.ledger_type == "savings":
                savings_bal += credit - debit
            lines.append({
                "txn_date": e.txn_date.isoformat() if e.txn_date else "",
                "txn_type": e.txn_type,
                "ledger_type": e.ledger_type,
                "reference": e.reference or "",
                "description": e.description or "",
                "debit": float(debit),
                "credit": float(credit),
                "posted_by": e.posted_by or "",
            })
        result.append({
            "member_no": member.member_no,
            "full_name": member.full_name,
            "lines": lines,
            "share_balance": float(share_bal),
            "savings_balance": float(savings_bal),
        })
    return result
