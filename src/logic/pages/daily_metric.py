def metric_placeholder(is_duration: bool) -> str:
    #return "0:00" if is_duration else "0"
    if is_duration:
        return "0:00"
    else:
        return "0"

def normalize_metric_definitions(rows) -> list[dict]:
    # rows from .mappings()
    out = []
    for r in rows:
        out.append(
            {
                "metric_key": r["metric_key"],
                "display_name": r["display_name"],
                "is_duration": bool(r["is_duration"]),
                "value_type": (r.get("value_type") or "double"),
                "unit": r.get("unit"),
            }
        )
    return out


def metric_specs_by_key(rows) -> dict[str, dict]:
    specs = {}
    for m in normalize_metric_definitions(rows):
        key = str(m["metric_key"])
        specs[key] = {
            "is_duration": bool(m.get("is_duration", False)),
            "value_type": str(m.get("value_type") or "double"),
            "unit": m.get("unit"),
            "display_name": m.get("display_name"),
        }
    return specs
