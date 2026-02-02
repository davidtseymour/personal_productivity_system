from datetime import timedelta
from src.helpers.general import is_valid_date, is_valid_time, combine_datetime, get_category_id_list


def validate_process_time_inputs(form_values, return_time_value=True):
    start_date = form_values.get("start_date", "")
    start_time = form_values.get("start_time", "")
    end_date = form_values.get("end_date", "")
    end_time = form_values.get("end_time", "")
    hours = form_values.get("hours", "")
    minutes = form_values.get("minutes", "")

    invalid_start_date = False
    invalid_start_time = False
    invalid_end_date = False
    invalid_end_time = False
    invalid_hours = False
    invalid_minutes = False

    if start_date not in (None, "") and not is_valid_date(start_date):
        invalid_start_date = True
    if end_date not in (None, "") and not is_valid_date(end_date):
        invalid_end_date = True
    if start_time not in (None, "") and not is_valid_time(start_time):
        invalid_start_time = True
    if end_time not in (None, "") and not is_valid_time(end_time):
        invalid_end_time = True

    # hours
    if hours not in (None, ""):
        try:
            h_val = int(hours)
            if h_val < 0:
                invalid_hours = True
        except Exception:
            invalid_hours = True
            h_val = None
    else:
        h_val = None

    # minutes (minutes-part 0..59)
    if minutes not in (None, ""):
        try:
            m_val = int(minutes)
            if not (0 <= m_val <= 59):
                invalid_minutes = True
        except Exception:
            invalid_minutes = True
            m_val = None
    else:
        m_val = None

    start_dt = combine_datetime(start_date, start_time)
    end_dt = combine_datetime(end_date, end_time)


    # ordering check if both exist
    if start_dt is not None and end_dt is not None and end_dt <= start_dt:
        invalid_start_date = True
        invalid_start_time = True
        invalid_end_date = True
        invalid_end_time = True

    # duration consistency check if both dt exist AND user supplied duration
    if (
        start_dt is not None
        and end_dt is not None
        and end_dt > start_dt
        and (hours not in (None, "") or minutes not in (None, ""))
        and not invalid_hours
        and not invalid_minutes
    ):
        total_minutes = int((end_dt - start_dt).total_seconds() // 60)
        implied_h = total_minutes // 60
        implied_m = total_minutes % 60
        if h_val is not None and h_val != implied_h:
            invalid_hours = True
        if m_val is not None and m_val != implied_m:
            invalid_minutes = True

    invalid = {
        "start_date": invalid_start_date,
        "start_time": invalid_start_time,
        "end_date": invalid_end_date,
        "end_time": invalid_end_time,
        "hours": invalid_hours,
        "minutes": invalid_minutes,
    }

    # ---------- build time_output ----------
    start_at = None
    end_at = None
    duration_min = None

    any_malformed_dt = invalid_start_date or invalid_start_time or invalid_end_date or invalid_end_time
    any_invalid_duration = invalid_hours or invalid_minutes

    # only attempt outputs if nothing is malformed
    if not any_malformed_dt and not any_invalid_duration:
        # 1) both datetimes available and ordered
        if start_dt is not None and end_dt is not None and end_dt > start_dt:
            start_at = start_dt
            end_at = end_dt
            duration_min = int((end_dt - start_dt).total_seconds() // 60)

        else:
            # 2) compute from one anchor + duration
            if h_val is not None or m_val is not None:
                dur = (h_val or 0) * 60 + (m_val or 0)
                if dur > 0:
                    if start_dt is not None and end_dt is None:
                        start_at = start_dt
                        duration_min = dur
                        end_at = start_dt + timedelta(minutes=dur)
                    elif end_dt is not None and start_dt is None:
                        end_at = end_dt
                        duration_min = dur
                        start_at = end_dt - timedelta(minutes=dur)

    date = start_at.date() if start_at else None
    time_output = {"start_at": start_at, "end_at": end_at, "duration_min": duration_min, 'date': date}

    if return_time_value:
        return invalid, time_output
    else:
        return invalid

def calculate_hh_mm_placeholders(form_values):
    start_date = form_values.get("start_date", "")
    start_time = form_values.get("start_time", "")
    end_date = form_values.get("end_date", "")
    end_time = form_values.get("end_time", "")

    start_dt = combine_datetime(start_date, start_time)
    end_dt = combine_datetime(end_date, end_time)


    # duration consistency check if both dt exist AND user supplied duration
    if (
        start_dt is not None
        and end_dt is not None
        and end_dt > start_dt
    ):
        diff = (end_dt - start_dt).total_seconds() / 60

        hours = int(diff // 60)
        minutes = int(diff % 60)

        placeholder_hours = str(hours)
        placeholder_mins = f"{minutes:02d}"
    else:
        placeholder_hours = ""
        placeholder_mins = ""

    return placeholder_hours, placeholder_mins

def _safe_int(x) -> int | None:
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def validate_category_complete(user_id, form_values):
    """
    Validate that:
      - category_id is present and belongs to the user (active categories)
      - subcategory and activity are non-empty (trimmed)

    Returns
    -------
    has_category_error : bool
    category_values : dict
        Normalized values with category_id as int|None and trimmed strings.
    """
    category_values = {
        "category_id": _safe_int(form_values.get("category_id")),  # <-- key + cast
        "subcategory": (form_values.get("subcategory") or "").strip(),
        "activity": (form_values.get("activity") or "").strip(),
        "notes": (form_values.get("notes") or "").strip(),
    }

    allowed_categories = get_category_id_list(user_id)  # list[int]

    has_category_error = (
        category_values["category_id"] is None
        or category_values["category_id"] not in allowed_categories
        or not category_values["subcategory"]
        or not category_values["activity"]
    )

    return has_category_error, category_values
