CANONICAL_CLIENT_CATEGORIES = (
    "salones-sociales",
    "mobiliario",
    "banquetes",
    "dj",
    "decoracion",
    "fotografia",
    "entretenimiento",
    "otros",
)

_CATEGORY_ALIASES = {
    "salones-sociales": "salones-sociales",
    "venue": "salones-sociales",
    "venues": "salones-sociales",
    "salon": "salones-sociales",
    "salones": "salones-sociales",
    "mobiliario": "mobiliario",
    "furniture": "mobiliario",
    "equipment": "mobiliario",
    "banquetes": "banquetes",
    "banquet": "banquetes",
    "entretenimiento": "entretenimiento",
    "entertainment": "entretenimiento",
    "decoracion": "decoracion",
    "decoración": "decoracion",
    "decoration": "decoracion",
    "fotografia": "fotografia",
    "fotografía": "fotografia",
    "photography": "fotografia",
    "dj": "dj",
    "otros": "otros",
    "other": "otros",
}


def normalize_client_category(
    raw_category: str | None,
    *,
    fallback_to_others: bool = True,
) -> str | None:
    value = str(raw_category or "").strip().lower()
    normalized = _CATEGORY_ALIASES.get(value)
    if normalized:
        return normalized
    if fallback_to_others:
        return "otros"
    return None
