"""CDA MC 2012-16 — minimum membership registry fields and choices."""

from datetime import date

# Section I — type/kind of membership (cooperative by-laws may add more)
MEMBERSHIP_TYPES = ("Regular", "Associate", "Institutional", "Honorary")

GENDERS = ("Male", "Female")

CIVIL_STATUSES = ("Single", "Married", "Widowed", "Separated", "Divorced")

EDUCATION_LEVELS = (
    "Elementary",
    "High School",
    "Vocational",
    "College",
    "Post Graduate",
    "Doctorate",
)

MEMBER_STATUSES = ("Active", "Inactive", "Terminated")

# Registry sections for UI labels (MC 2012-16 Section 6)
REGISTRY_SECTIONS = (
    ("registry", "Registry Information (A–C)"),
    ("acceptance", "Membership Upon Acceptance (I)"),
    ("profile", "Member Profile (II)"),
    ("termination", "Termination of Membership (III)"),
)


def build_full_name(last_name, first_name, middle_name=None):
    """Format registry name: Last, First Middle."""
    first = (first_name or "").strip()
    middle = (middle_name or "").strip()
    last = (last_name or "").strip()
    given = " ".join(p for p in (first, middle) if p)
    if last and given:
        return f"{last}, {given}"
    return given or last


def member_age(birth_date, on_date=None):
    if not birth_date:
        return None
    today = on_date or date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)
