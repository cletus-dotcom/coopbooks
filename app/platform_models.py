"""Cooperative registry and module subscription models."""

from app import db
from app.models import local_time


class CoopRegistry(db.Model):
    """Registered cooperative tenant."""

    __tablename__ = "coop_registry"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    db_name = db.Column(db.String(80), unique=True, nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False)
    registration_no = db.Column(db.String(50))
    tin = db.Column(db.String(30))
    rdo = db.Column(db.String(80))
    coop_type = db.Column(db.String(80))
    address = db.Column(db.String(255))
    fiscal_year_end = db.Column(db.String(20), default="December 31")
    logo_filename = db.Column(db.String(120))
    logo_data = db.Column(db.LargeBinary)
    logo_mime_type = db.Column(db.String(80))
    contact_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=local_time)

    modules = db.relationship(
        "CoopModuleSubscription",
        back_populates="coop",
        cascade="all, delete-orphan",
    )

    STATUSES = ("Active", "Suspended", "Pending")

    @property
    def is_active(self):
        return self.status == "Active"


class CoopModuleSubscription(db.Model):
    """Module subscription for a cooperative."""

    __tablename__ = "coop_module_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    coop_id = db.Column(db.Integer, db.ForeignKey("coop_registry.id"), nullable=False)
    module_key = db.Column(db.String(40), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    activated_at = db.Column(db.DateTime, default=local_time)

    coop = db.relationship("CoopRegistry", back_populates="modules")

    __table_args__ = (
        db.UniqueConstraint("coop_id", "module_key", name="uq_coop_module"),
    )


# PlatformUser removed — use User.role == "PlatformAdmin" instead.
