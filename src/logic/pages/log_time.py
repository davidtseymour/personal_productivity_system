from datetime import datetime
from src.helpers.general import validate_time_inputs

TWO_HOURS_MIN = 120


def validate_task_fields(
    start_date, start_time, end_date, end_time, hours, minutes, include_placeholders=True
):
    inv_start_date, inv_start_time, inv_end_date, inv_end_time, inv_hours, inv_minutes = validate_time_inputs(
        start_date, start_time, end_date, end_time, hours, minutes
    )

    def parse_dt(d, t):
        if not d or not t:
            return None
        try:
            return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            return None

    def to_int(v):
        if v in (None, "", "None"):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    start_dt = parse_dt(start_date, start_time)
    end_dt = parse_dt(end_date, end_time)
    h = to_int(hours)
    m = to_int(minutes)

    # Compute duration if possible
    duration_min = None
    if (h is not None) or (m is not None):
        total = (h or 0) * 60 + (m or 0)
        if total > 0:
            duration_min = total
    elif start_dt and end_dt:
        diff_min = (end_dt - start_dt).total_seconds() / 60
        if diff_min > 0:
            duration_min = int(diff_min)

    any_invalid = any([inv_start_date, inv_start_time, inv_end_date, inv_end_time, inv_hours, inv_minutes])

    # Cosmetic warning
    warn = (duration_min is not None) and (duration_min > TWO_HOURS_MIN) and (not any_invalid)
    warn_class = "warning" if warn else ""
    warn_text = "Warning: entry exceeds 2 hours." if warn else ""

    if include_placeholders:
        ph = ""
        pm = ""
        if start_dt and end_dt:
            diff_min = (end_dt - start_dt).total_seconds() / 60
            if diff_min > 0:
                ph = str(int(diff_min // 60))
                pm = f"{int(diff_min % 60):02d}"

        return (
            inv_start_date, inv_start_time, inv_end_date, inv_end_time, inv_hours, inv_minutes,
            warn_class, warn_class, warn_text, ph, pm,
        )

    return inv_start_date, inv_start_time, inv_end_date, inv_end_time, inv_hours, inv_minutes
