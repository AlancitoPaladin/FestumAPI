import re
from urllib.parse import urlparse


PHONE_ALLOWED_CHARS_RE = re.compile(r"^[\d+\-()\s]+$")
PHONE_DIGITS_RE = re.compile(r"\D")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SOCIAL_HANDLE_RE = re.compile(r"^@?[A-Za-z0-9._]{1,30}$")


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def normalize_phone(value: str | None) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""

    if not PHONE_ALLOWED_CHARS_RE.fullmatch(normalized):
        raise ValueError("Phone fields only accept numbers and basic phone characters")

    has_plus = normalized.startswith("+")
    digits = PHONE_DIGITS_RE.sub("", normalized)
    if not digits:
        raise ValueError("Phone number is invalid")
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("Phone number must contain between 8 and 15 digits")

    return f"+{digits}" if has_plus else digits


def normalize_email(value: str | None) -> str:
    normalized = normalize_text(value).lower()
    if not normalized:
        return ""
    if not EMAIL_RE.fullmatch(normalized):
        raise ValueError("Email address is invalid")
    return normalized


def normalize_website(value: str | None) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Website must be a valid http or https URL")
    return normalized


def normalize_social_handle(value: str | None) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    if not SOCIAL_HANDLE_RE.fullmatch(normalized):
        raise ValueError("Social handle is invalid")
    return normalized if normalized.startswith("@") else f"@{normalized}"
