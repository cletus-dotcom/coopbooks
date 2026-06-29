from functools import wraps

from flask import flash, jsonify, redirect, request, session, url_for

from app.config import can_manage_coops, can_post_entries, is_admin_role, normalize_role
from app.modules_config import module_for_path
from app.tenant_manager import coop_has_module, switch_tenant_bind

PLATFORM_PUBLIC_ENDPOINTS = frozenset({
    "main_routes.coop_logo",
})

PUBLIC_ENDPOINTS = frozenset({
    "main_routes.index",
    "main_routes.login",
    "main_routes.logout",
    "main_routes.api_coop_list",
}) | PLATFORM_PUBLIC_ENDPOINTS

STAFF_ENDPOINTS = frozenset({
    "main_routes.members_add",
    "main_routes.member_ledger_add",
    "main_routes.journal_new",
    "main_routes.api_next_member_no",
})

PLATFORM_ADMIN_PREFIXES = ("/admin/coops", "/admin/migration")


def _wants_json_response():
    if request.is_json or request.path.startswith("/api/"):
        return True
    if request.method in ("POST", "PUT", "DELETE") and request.path.startswith("/admin/"):
        return True
    return False


def _deny_login_required():
    if _wants_json_response():
        return jsonify({
            "status": "error",
            "msg": "Authentication required.",
            "success": False,
        }), 401
    flash("Please login first.", "warning")
    return redirect(url_for("main_routes.login", next=request.path))


def _deny_forbidden(message):
    if _wants_json_response():
        return jsonify({
            "status": "error",
            "msg": message,
            "success": False,
        }), 403
    flash(message, "danger")
    return redirect(url_for("main_routes.dashboard"))


def _get_session_user():
    from app.models import User

    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def _refresh_session_user(user):
    session["username"] = user.username
    session["fullname"] = user.full_name
    session["role"] = normalize_role(user.role)


def _bind_tenant_from_session():
    if session.get("is_platform_admin"):
        return None
    slug = session.get("coop_slug")
    if not slug:
        return None
    try:
        return switch_tenant_bind(slug)
    except ValueError:
        return None


def register_route_guards(blueprint):
    @blueprint.before_request
    def enforce_route_guards():
        endpoint = request.endpoint
        if endpoint is None or endpoint == "static":
            return None

        if endpoint in PUBLIC_ENDPOINTS:
            return None

        if session.get("is_platform_admin"):
            if (
                request.path.startswith("/admin/coops")
                or request.path.startswith("/admin/migration")
                or endpoint in PUBLIC_ENDPOINTS
            ):
                return None
            return redirect(url_for("main_routes.admin_coops"))

        if "username" not in session:
            return _deny_login_required()

        if not session.get("is_platform_admin"):
            registry = _bind_tenant_from_session()
            if not registry:
                session.clear()
                flash("Cooperative session expired. Please log in again.", "warning")
                return redirect(url_for("main_routes.login"))

            if registry.status != "Active":
                session.clear()
                flash("This cooperative account is suspended.", "warning")
                return redirect(url_for("main_routes.login"))

            module_key = module_for_path(request.path)
            if module_key and module_key != "about" and not coop_has_module(module_key, registry.id):
                return _deny_forbidden(
                    f"The '{module_key}' module is not active for your subscription."
                )

        if not session.get("is_platform_admin"):
            user = _get_session_user()
            if not user:
                session.clear()
                return _deny_login_required()

            if (user.status or "Active") != "Active":
                session.clear()
                flash("Your account is inactive. Contact an administrator.", "warning")
                return redirect(url_for("main_routes.login"))

            _refresh_session_user(user)
            role = session.get("role")
        else:
            role = "PlatformAdmin"

        if request.path.startswith("/admin/coops"):
            if not can_manage_coops(session):
                return _deny_forbidden("Platform administrator access required.")
            return None

        if request.path.startswith("/admin/migration"):
            if not can_manage_coops(session):
                return _deny_forbidden("Platform administrator access required.")
            return None

        if request.path.startswith("/admin"):
            if not is_admin_role(role):
                return _deny_forbidden("Access denied. Admins only.")

        if endpoint in STAFF_ENDPOINTS:
            if not can_post_entries(role):
                return _deny_forbidden(
                    "You do not have permission to perform this action."
                )

        return None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session and not session.get("is_platform_admin"):
            return _deny_login_required()
        return func(*args, **kwargs)

    return wrapper


def staff_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return _deny_login_required()
        if not can_post_entries(session.get("role")):
            return _deny_forbidden(
                "You do not have permission to perform this action."
            )
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session and not session.get("is_platform_admin"):
            return _deny_login_required()
        if not is_admin_role(session.get("role")) and not session.get("is_platform_admin"):
            return _deny_forbidden("Access denied. Admins only.")
        return func(*args, **kwargs)

    return wrapper


def platform_admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not can_manage_coops(session):
            return _deny_forbidden("Platform administrator access required.")
        return func(*args, **kwargs)

    return wrapper
