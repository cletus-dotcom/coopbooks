from datetime import date

from decimal import Decimal

from werkzeug.security import generate_password_hash

from app import db
from app.models import Account, Cooperative, JournalEntry, JournalLine, Member, MemberLedger, User, local_time
from app.seed_data import CDA_CHART_OF_ACCOUNTS, SAMPLE_JOURNALS, SAMPLE_MEMBERS
from app.member_service import create_opening_ledger_entries, member_has_ledger, record_ledger_entry


def seed_database():
    seed_tenant_database()


def seed_tenant_database(include_samples=True):
    _seed_admin_user()
    _seed_cooperative()
    _seed_chart_of_accounts()
    if include_samples:
        _seed_members()
        _seed_sample_journals()
        _seed_member_ledgers()


def _seed_admin_user():
    if User.query.filter_by(username="Admin").first():
        return

    admin = User(
        username="Admin",
        full_name="System Administrator",
        email="admin@coop.local",
        role="Admin",
        status="Active",
        password_hash=generate_password_hash("123"),
    )
    db.session.add(admin)
    db.session.commit()


def _seed_cooperative():
    if Cooperative.query.first():
        return

    db.session.add(Cooperative(
        name="Sample Primary Multi-Purpose Cooperative",
        registration_no="CDA-XXXX-XXXXX",
        coop_type="Primary Multi-Purpose Cooperative",
        address="Philippines",
        fiscal_year_end="December 31",
    ))
    db.session.commit()


def _seed_chart_of_accounts():
    if Account.query.count() > 0:
        return

    for code, name, account_type, category, normal_balance in CDA_CHART_OF_ACCOUNTS:
        db.session.add(Account(
            code=code,
            name=name,
            account_type=account_type,
            category=category,
            normal_balance=normal_balance,
        ))
    db.session.commit()


def _seed_members():
    if Member.query.count() > 0:
        return

    today = local_time().date()
    for member_no, full_name, share, savings in SAMPLE_MEMBERS:
        db.session.add(Member(
            member_no=member_no,
            full_name=full_name,
            membership_date=today,
            share_capital=share,
            savings_balance=savings,
        ))
    db.session.commit()


def _entry_date_months_ago(months_ago):
    today = local_time().date()
    month = today.month - months_ago
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(today.day, 28)
    return date(year, month, day)


def _seed_sample_journals():
    if JournalEntry.query.count() > 0:
        return

    accounts = {a.code: a for a in Account.query.all()}

    for journal in SAMPLE_JOURNALS:
        entry = JournalEntry(
            entry_no=journal["entry_no"],
            entry_date=_entry_date_months_ago(journal.get("months_ago", 0)),
            description=journal["description"],
            reference=journal["reference"],
            posted_by="Admin",
        )
        db.session.add(entry)
        db.session.flush()

        for code, debit, credit, memo in journal["lines"]:
            account = accounts.get(code)
            if not account:
                continue
            db.session.add(JournalLine(
                entry_id=entry.id,
                account_id=account.id,
                debit=Decimal(str(debit)),
                credit=Decimal(str(credit)),
                memo=memo,
            ))

    db.session.commit()


def _seed_member_ledgers():
    members = Member.query.order_by(Member.member_no).all()
    if not members:
        return

    for member in members:
        if not member_has_ledger(member.id):
            create_opening_ledger_entries(
                member,
                posted_by="Admin",
                share_amount=member.share_capital,
                savings_amount=member.savings_balance,
            )

    if MemberLedger.query.filter(MemberLedger.txn_type != "OPENING_BALANCE").count() > 0:
        return

    sample_txns = [
        ("M-001", "SAVINGS_DEPOSIT", "500", "OR-1001", "Monthly savings"),
        ("M-002", "SHARE_SUBSCRIPTION", "2000", "OR-1002", "Additional shares"),
        ("M-002", "SAVINGS_DEPOSIT", "1000", "OR-1003", "Payroll savings"),
        ("M-003", "LOAN_RELEASE", "5000", "LV-003", "Emergency loan"),
        ("M-003", "LOAN_PAYMENT", "800", "OR-1004", "Loan amortization"),
        ("M-004", "SAVINGS_DEPOSIT", "750", "OR-1005", "Savings deposit"),
        ("M-005", "SHARE_SUBSCRIPTION", "500", "OR-1006", "Share build-up"),
    ]

    today = local_time().date()
    for member_no, txn_type, amount, ref, desc in sample_txns:
        member = Member.query.filter_by(member_no=member_no).first()
        if not member:
            continue
        is_debit = txn_type in ("SHARE_REDEMPTION", "SAVINGS_WITHDRAWAL", "LOAN_PAYMENT")
        record_ledger_entry(
            member, today, txn_type, amount,
            reference=ref, description=desc, posted_by="Admin",
            is_debit=is_debit,
        )

    db.session.commit()
