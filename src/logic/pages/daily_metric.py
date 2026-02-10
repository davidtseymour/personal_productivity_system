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
            }
        )
    return out