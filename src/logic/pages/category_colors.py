from collections.abc import Iterable

PLOTLY_COLORWAY = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
]


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def tint_hex_color(hex_color: str, tint: float = 0.0) -> str:
    """
    Tint a hex color toward white by fraction `tint` in [0, 1].
    """
    t = max(0.0, min(1.0, float(tint)))
    normalized = hex_color.lstrip("#")
    if len(normalized) != 6:
        return hex_color

    try:
        r = int(normalized[0:2], 16)
        g = int(normalized[2:4], 16)
        b = int(normalized[4:6], 16)
    except ValueError:
        return hex_color

    r = round(r + ((255 - r) * t))
    g = round(g + ((255 - g) * t))
    b = round(b + ((255 - b) * t))
    return f"#{r:02X}{g:02X}{b:02X}"


def ordered_category_color_map(category_order: Iterable[str], tint: float = 0.0) -> dict[str, str]:
    """
    Build a stable color map for categories using Plotly's default colorway.
    """
    ordered = _dedupe_preserve_order(category_order)
    color_map: dict[str, str] = {}
    for idx, category in enumerate(ordered):
        base = PLOTLY_COLORWAY[idx % len(PLOTLY_COLORWAY)]
        color_map[category] = tint_hex_color(base, tint=tint)
    return color_map
