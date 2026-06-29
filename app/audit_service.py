"""Audit trail logging for BIR CAS compliance (Annex B Item 8)."""

import json

from flask import request, session

from app import db
from app.models import AuditLog, local_time


def _actor():
    return session.get("fullname") or session.get("username") or "System"


def _actor_id():
    return session.get("user_id")


def log_audit(action, entity_type, entity_id=None, entity_label="", details=None):
    """Record a CREATE, UPDATE, or DELETE activity."""
    entry = AuditLog(
        action=action.upper(),
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        entity_label=(entity_label or "")[:255],
        details=json.dumps(details or {}, default=str),
        username=_actor(),
        user_id=_actor_id(),
        ip_address=(request.remote_addr or "")[:45] if request else None,
        created_at=local_time(),
    )
    db.session.add(entry)
    return entry


def audit_trail_rows(limit=500, entity_type=None):
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    rows = query.limit(limit).all()
    return [_serialize_log(row) for row in rows]


def _serialize_log(row):
    details = {}
    if row.details:
        try:
            details = json.loads(row.details)
        except json.JSONDecodeError:
            details = {"raw": row.details}
    return {
        "id": row.id,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id or "",
        "entity_label": row.entity_label or "",
        "username": row.username or "",
        "ip_address": row.ip_address or "",
        "details": details,
    }
