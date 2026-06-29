"""Application modules — subscription-gated features per cooperative."""

APP_MODULES = {
    "dashboard": {
        "label": "Dashboard",
        "icon": "bi-speedometer2",
        "nav_key": "dashboard",
        "route_prefixes": ("/dashboard", "/api/dashboard"),
        "default_enabled": True,
        "core": True,
    },
    "journal": {
        "label": "General Journal",
        "icon": "bi-journal-text",
        "nav_key": "journal",
        "route_prefixes": ("/journal",),
        "default_enabled": True,
        "core": True,
    },
    "accounts": {
        "label": "Chart of Accounts",
        "icon": "bi-list-columns",
        "nav_key": "accounts",
        "route_prefixes": ("/accounts",),
        "default_enabled": True,
        "core": True,
    },
    "members": {
        "label": "Members",
        "icon": "bi-people",
        "nav_key": "members",
        "route_prefixes": ("/members", "/api/members"),
        "default_enabled": True,
        "core": True,
    },
    "reports": {
        "label": "Reports",
        "icon": "bi-file-earmark-bar-graph",
        "nav_key": "reports",
        "route_prefixes": ("/reports",),
        "default_enabled": True,
        "core": False,
    },
    "bir_cas": {
        "label": "BIR CAS Docs",
        "icon": "bi-folder2-open",
        "nav_key": "documentation",
        "route_prefixes": ("/documentation",),
        "default_enabled": False,
        "core": False,
    },
    "admin_users": {
        "label": "User Management",
        "icon": "bi-person-gear",
        "nav_key": "users",
        "route_prefixes": ("/admin/users",),
        "default_enabled": True,
        "core": True,
    },
}

ALWAYS_ENABLED_MODULES = frozenset({"about"})


def default_module_keys():
    return [key for key, spec in APP_MODULES.items() if spec.get("default_enabled")]


def module_for_path(path):
    if path.startswith("/about"):
        return "about"
    if path.startswith("/admin/coops"):
        return None
    for key, spec in APP_MODULES.items():
        for prefix in spec.get("route_prefixes", ()):
            if path.startswith(prefix):
                return key
    return None


def nav_modules(subscribed_keys):
    subscribed = set(subscribed_keys) | ALWAYS_ENABLED_MODULES
    items = []
    for key, spec in APP_MODULES.items():
        if key not in subscribed:
            continue
        items.append({"key": key, **spec})
    return items
