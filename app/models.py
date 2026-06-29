from datetime import datetime

import pytz
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


TENANT_BIND = "tenant"


def local_time():
    philippine_tz = pytz.timezone("Asia/Manila")
    return datetime.now(philippine_tz).replace(tzinfo=None)


class TenantModel(db.Model):
    __abstract__ = True
    __bind_key__ = TENANT_BIND


class User(TenantModel):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))
    email = db.Column(db.String(120), unique=True)
    role = db.Column(db.String(20), default="Member")
    status = db.Column(db.String(20), default="Active")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Cooperative(TenantModel):
    __tablename__ = "cooperatives"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    registration_no = db.Column(db.String(50))
    tin = db.Column(db.String(30))
    rdo = db.Column(db.String(80))
    coop_type = db.Column(db.String(80))
    address = db.Column(db.String(255))
    fiscal_year_end = db.Column(db.String(20), default="December 31")
    created_at = db.Column(db.DateTime, default=local_time)


class Account(TenantModel):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(80))
    normal_balance = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    lines = db.relationship("JournalLine", back_populates="account")


class Member(TenantModel):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    member_no = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    membership_date = db.Column(db.Date)
    share_capital = db.Column(db.Numeric(14, 2), default=0)
    savings_balance = db.Column(db.Numeric(14, 2), default=0)
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=local_time)

    MEMBER_STATUSES = ("Active", "Inactive")

    ledger_entries = db.relationship(
        "MemberLedger",
        back_populates="member",
        cascade="all, delete-orphan",
    )


class MemberLedger(TenantModel):
    __tablename__ = "member_ledger"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    txn_date = db.Column(db.Date, nullable=False)
    txn_type = db.Column(db.String(40), nullable=False)
    ledger_type = db.Column(db.String(20), nullable=False)
    reference = db.Column(db.String(80))
    description = db.Column(db.String(255))
    debit = db.Column(db.Numeric(14, 2), default=0)
    credit = db.Column(db.Numeric(14, 2), default=0)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id"))
    posted_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=local_time)

    member = db.relationship("Member", back_populates="ledger_entries")
    journal_entry = db.relationship("JournalEntry", backref="member_ledger_rows")

    LEDGER_TYPES = ("share", "savings", "loan")
    TXN_TYPES = (
        "OPENING_BALANCE",
        "SHARE_SUBSCRIPTION",
        "SHARE_REDEMPTION",
        "SAVINGS_DEPOSIT",
        "SAVINGS_WITHDRAWAL",
        "LOAN_RELEASE",
        "LOAN_PAYMENT",
        "LOAN_INTEREST",
        "PATRONAGE_REFUND",
        "INTEREST_ON_SHARE",
    )


class JournalEntry(TenantModel):
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    entry_no = db.Column(db.String(30), unique=True, nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))
    reference = db.Column(db.String(80))
    posted_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=local_time)

    lines = db.relationship(
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
    )


class JournalLine(TenantModel):
    __tablename__ = "journal_lines"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    debit = db.Column(db.Numeric(14, 2), default=0)
    credit = db.Column(db.Numeric(14, 2), default=0)
    memo = db.Column(db.String(200))

    entry = db.relationship("JournalEntry", back_populates="lines")
    account = db.relationship("Account", back_populates="lines")


class AuditLog(TenantModel):
    """BIR CAS audit trail — who created, edited, or deleted records."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=local_time, nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.String(80))
    entity_label = db.Column(db.String(255))
    details = db.Column(db.Text)
    username = db.Column(db.String(150))
    user_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))

