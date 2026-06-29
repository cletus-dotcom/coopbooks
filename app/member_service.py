from datetime import datetime
from decimal import Decimal, InvalidOperation

from app import db
from app.models import Member, MemberLedger, local_time

MEMBER_STATUSES = list(Member.MEMBER_STATUSES)

TXN_TYPE_LABELS = {
    "OPENING_BALANCE": "Opening Balance",
    "SHARE_SUBSCRIPTION": "Share Subscription",
    "SHARE_REDEMPTION": "Share Redemption",
    "SAVINGS_DEPOSIT": "Savings Deposit",
    "SAVINGS_WITHDRAWAL": "Savings Withdrawal",
    "LOAN_RELEASE": "Loan Release",
    "LOAN_PAYMENT": "Loan Payment",
    "LOAN_INTEREST": "Loan Interest",
    "PATRONAGE_REFUND": "Patronage Refund",
    "INTEREST_ON_SHARE": "Interest on Share Capital",
}

TXN_TYPE_LEDGER = {
    "OPENING_BALANCE": None,
    "SHARE_SUBSCRIPTION": "share",
    "SHARE_REDEMPTION": "share",
    "SAVINGS_DEPOSIT": "savings",
    "SAVINGS_WITHDRAWAL": "savings",
    "LOAN_RELEASE": "loan",
    "LOAN_PAYMENT": "loan",
    "LOAN_INTEREST": "loan",
    "PATRONAGE_REFUND": "share",
    "INTEREST_ON_SHARE": "share",
}

POSTABLE_TXN_TYPES = [
    "SHARE_SUBSCRIPTION",
    "SHARE_REDEMPTION",
    "SAVINGS_DEPOSIT",
    "SAVINGS_WITHDRAWAL",
    "LOAN_RELEASE",
    "LOAN_PAYMENT",
    "LOAN_INTEREST",
    "PATRONAGE_REFUND",
    "INTEREST_ON_SHARE",
]


def display_txn_type(txn_type):
    return TXN_TYPE_LABELS.get(txn_type, txn_type.replace("_", " ").title())


def next_member_no():
    prefix = "M-"
    latest = (
        Member.query
        .filter(Member.member_no.like(f"{prefix}%"))
        .order_by(Member.member_no.desc())
        .first()
    )
    if not latest:
        return f"{prefix}001"
    try:
        seq = int(latest.member_no.replace(prefix, "")) + 1
    except ValueError:
        seq = Member.query.count() + 1
    return f"{prefix}{seq:03d}"


def member_totals(members):
    share = sum(Decimal(str(m.share_capital or 0)) for m in members)
    savings = sum(Decimal(str(m.savings_balance or 0)) for m in members)
    return {
        "total_share_capital": float(share),
        "total_savings": float(savings),
        "active_count": sum(1 for m in members if m.status == "Active"),
    }


def member_has_ledger(member_id):
    return MemberLedger.query.filter_by(member_id=member_id).count() > 0


def ledger_balance(member_id, ledger_type):
    rows = MemberLedger.query.filter_by(member_id=member_id, ledger_type=ledger_type).all()
    credits = sum(Decimal(str(r.credit or 0)) for r in rows)
    debits = sum(Decimal(str(r.debit or 0)) for r in rows)
    return credits - debits


def sync_member_balances(member):
    member.share_capital = ledger_balance(member.id, "share")
    member.savings_balance = ledger_balance(member.id, "savings")


def serialize_ledger_row(row, running_share=None, running_savings=None, running_loan=None):
    data = {
        "id": row.id,
        "txn_date": row.txn_date.isoformat() if row.txn_date else "",
        "txn_type": row.txn_type,
        "txn_type_label": display_txn_type(row.txn_type),
        "ledger_type": row.ledger_type,
        "reference": row.reference or "",
        "description": row.description or "",
        "debit": float(row.debit or 0),
        "credit": float(row.credit or 0),
        "posted_by": row.posted_by or "",
        "journal_entry_id": row.journal_entry_id,
        "journal_entry_no": row.journal_entry.entry_no if row.journal_entry else None,
    }
    if running_share is not None:
        data["running_share"] = float(running_share)
    if running_savings is not None:
        data["running_savings"] = float(running_savings)
    if running_loan is not None:
        data["running_loan"] = float(running_loan)
    return data


def member_ledger_history(member_id):
    rows = (
        MemberLedger.query
        .filter_by(member_id=member_id)
        .order_by(MemberLedger.txn_date.asc(), MemberLedger.id.asc())
        .all()
    )

    running = {"share": Decimal("0"), "savings": Decimal("0"), "loan": Decimal("0")}
    history = []

    for row in rows:
        lt = row.ledger_type
        running[lt] += Decimal(str(row.credit or 0)) - Decimal(str(row.debit or 0))
        history.append(serialize_ledger_row(
            row,
            running_share=running["share"],
            running_savings=running["savings"],
            running_loan=running["loan"],
        ))

    return list(reversed(history))


def member_ledger_summary(member_id):
    count = MemberLedger.query.filter_by(member_id=member_id).count()
    share_bal = ledger_balance(member_id, "share")
    savings_bal = ledger_balance(member_id, "savings")
    loan_bal = ledger_balance(member_id, "loan")
    return {
        "has_ledger": count > 0,
        "transaction_count": count,
        "share_balance": float(share_bal),
        "savings_balance": float(savings_bal),
        "loan_balance": float(loan_bal),
    }


def record_ledger_entry(member, txn_date, txn_type, amount, ledger_type=None,
                        reference=None, description=None, posted_by=None,
                        journal_entry_id=None, is_debit=False):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if ledger_type is None:
        ledger_type = TXN_TYPE_LEDGER.get(txn_type)
    if not ledger_type:
        raise ValueError("Ledger type is required for this transaction.")

    debit = amount if is_debit else Decimal("0")
    credit = amount if not is_debit else Decimal("0")

    row = MemberLedger(
        member_id=member.id,
        txn_date=txn_date,
        txn_type=txn_type,
        ledger_type=ledger_type,
        reference=reference,
        description=description,
        debit=debit,
        credit=credit,
        journal_entry_id=journal_entry_id,
        posted_by=posted_by,
    )
    db.session.add(row)
    sync_member_balances(member)
    return row


def create_opening_ledger_entries(member, posted_by="System", share_amount=None, savings_amount=None):
    if member_has_ledger(member.id):
        return

    share_amt = Decimal(str(share_amount if share_amount is not None else member.share_capital or 0))
    savings_amt = Decimal(str(savings_amount if savings_amount is not None else member.savings_balance or 0))
    txn_date = member.membership_date or local_time().date()

    if share_amt > 0:
        record_ledger_entry(
            member,
            txn_date,
            "OPENING_BALANCE",
            share_amt,
            ledger_type="share",
            reference="OPEN",
            description="Opening share capital balance",
            posted_by=posted_by,
        )
    if savings_amt > 0:
        record_ledger_entry(
            member,
            txn_date,
            "OPENING_BALANCE",
            savings_amt,
            ledger_type="savings",
            reference="OPEN",
            description="Opening savings balance",
            posted_by=posted_by,
        )


def parse_ledger_form(data, member):
    txn_type = (data.get("txn_type") or "").strip()
    txn_date = (data.get("txn_date") or "").strip() or local_time().date().isoformat()
    amount_raw = (data.get("amount") or "").strip()
    reference = (data.get("reference") or "").strip() or None
    description = (data.get("description") or "").strip() or None

    if txn_type not in POSTABLE_TXN_TYPES:
        return None, "Invalid transaction type."

    try:
        txn_date_parsed = datetime.strptime(txn_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Invalid transaction date."

    try:
        amount = Decimal(amount_raw)
    except InvalidOperation:
        return None, "Invalid amount."

    if amount <= 0:
        return None, "Amount must be greater than zero."

    is_debit = txn_type in (
        "SHARE_REDEMPTION",
        "SAVINGS_WITHDRAWAL",
        "LOAN_PAYMENT",
    )

    ledger_type = TXN_TYPE_LEDGER.get(txn_type)
    current_balance = ledger_balance(member.id, ledger_type)
    if is_debit and amount > current_balance:
        return None, f"Insufficient {ledger_type} balance for this transaction."

    return {
        "txn_type": txn_type,
        "txn_date": txn_date_parsed,
        "amount": amount,
        "reference": reference,
        "description": description,
        "is_debit": is_debit,
    }, None


def serialize_member(member):
    summary = member_ledger_summary(member.id)
    return {
        "id": member.id,
        "member_no": member.member_no,
        "full_name": member.full_name,
        "email": member.email or "",
        "phone": member.phone or "",
        "address": member.address or "",
        "membership_date": member.membership_date.isoformat() if member.membership_date else "",
        "share_capital": float(member.share_capital or 0),
        "savings_balance": float(member.savings_balance or 0),
        "status": member.status or "Active",
        "created_at": member.created_at.isoformat() if member.created_at else "",
        "has_ledger": summary["has_ledger"],
        "transaction_count": summary["transaction_count"],
    }


def parse_member_form(data):
    member_no = (data.get("member_no") or "").strip() or next_member_no()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    address = (data.get("address") or "").strip() or None
    membership_date = (data.get("membership_date") or "").strip() or local_time().date().isoformat()
    status = (data.get("status") or "Active").strip()

    if not full_name:
        return None, "Full name is required."

    if status not in MEMBER_STATUSES:
        return None, "Invalid member status."

    if Member.query.filter_by(member_no=member_no).first():
        return None, f"Member number {member_no} already exists."

    try:
        membership_date_parsed = datetime.strptime(membership_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Invalid membership date."

    try:
        share_capital = Decimal(str(data.get("share_capital") or "0"))
        savings_balance = Decimal(str(data.get("savings_balance") or "0"))
    except InvalidOperation:
        return None, "Invalid amount for share capital or savings."

    if share_capital < 0 or savings_balance < 0:
        return None, "Amounts cannot be negative."

    return {
        "member_no": member_no,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "address": address,
        "membership_date": membership_date_parsed,
        "share_capital": share_capital,
        "savings_balance": savings_balance,
        "status": status,
    }, None
