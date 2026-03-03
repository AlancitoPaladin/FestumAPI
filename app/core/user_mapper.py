from typing import Any


def to_public_user_document(user_data: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_data)
    data.pop("password_hash", None)

    if "first_name" not in data or "last_name" not in data:
        full_name = str(data.get("full_name", "")).strip()
        name_parts = full_name.split() if full_name else []
        data["first_name"] = data.get("first_name") or (name_parts[0].title() if name_parts else "User")
        data["last_name"] = data.get("last_name") or (
            " ".join(name_parts[1:]).title() if len(name_parts) > 1 else "Unknown"
        )

    data.pop("full_name", None)
    data["is_active"] = bool(data.get("is_active", True))
    data.setdefault("role", "client")
    data.setdefault("phone", None)
    data.setdefault("birth_date", None)
    return data
