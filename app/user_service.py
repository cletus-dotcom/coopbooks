from werkzeug.security import generate_password_hash

from app.config import USER_ROLES, assignable_user_roles, is_valid_user_role, normalize_role
from app.models import User


def list_users():
    return User.query.order_by(User.user_id.asc()).all()


def serialize_user(user):
    return {
        "id": user.user_id,
        "username": user.username,
        "full_name": user.full_name or "",
        "email": user.email or "",
        "role": user.role or "Member",
        "status": user.status or "Active",
    }


def parse_user_form(data, user_id=None, require_password=False, current_role=None):
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip() or None
    role = (data.get("role") or "").strip()
    status = (data.get("status") or "Active").strip()
    password = (data.get("password") or "").strip()

    if not username or not full_name or not role:
        return None, "Username, full name, and role are required."

    if not is_valid_user_role(role):
        return None, "Invalid role selected."

    normalized_role = normalize_role(role)
    allowed = assignable_user_roles(current_role)
    if normalized_role not in allowed:
        return None, "You cannot assign that role."

    if status not in ("Active", "Inactive"):
        return None, "Invalid status."

    existing = User.query.filter_by(username=username).first()
    if existing and existing.user_id != user_id:
        return None, "Username already exists."

    if email:
        email_taken = User.query.filter_by(email=email).first()
        if email_taken and email_taken.user_id != user_id:
            return None, "Email already exists."

    if require_password and not password:
        return None, "Password is required for new users."

    result = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "role": normalized_role,
        "status": status,
    }
    if password:
        result["password_hash"] = generate_password_hash(password)

    return result, None


def apply_user_update(user, parsed):
    user.username = parsed["username"]
    user.full_name = parsed["full_name"]
    user.email = parsed["email"]
    user.role = parsed["role"]
    user.status = parsed["status"]
    if "password_hash" in parsed:
        user.password_hash = parsed["password_hash"]
