import math

from datetime import datetime, timedelta
from src.data_access.db import load_category_list, load_category_id_to_name

# Validating time imports - used in Logging time and editing time

def validate_time_inputs(
        start_date,
        start_time,
        end_date,
        end_time,
        hours,
        minutes,
):
    # --- per-field validation ---
    invalid_start_date = False
    invalid_start_time = False
    invalid_end_date = False
    invalid_end_time = False
    invalid_hours = False
    invalid_minutes = False

    # Validate date/time formats (only mark invalid if non-empty)
    if start_date not in (None, "") and not is_valid_date(start_date):
        invalid_start_date = True

    if end_date not in (None, "") and not is_valid_date(end_date):
        invalid_end_date = True

    if start_time not in (None, "") and not is_valid_time(start_time):
        invalid_start_time = True

    if end_time not in (None, "") and not is_valid_time(end_time):
        invalid_end_time = True

    # Validate hours: numeric integer, >= 0 if provided
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

    # Validate minutes: numeric integer, 0-59 if provided
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

    # --- cross-field check: end > start ---
    start_dt = combine_datetime(start_date, start_time)
    end_dt = combine_datetime(end_date, end_time)

    if (
            start_dt is not None
            and end_dt is not None
            and end_dt <= start_dt
    ):
        # Mark both start and end as invalid if ordering is wrong
        invalid_start_date = True
        invalid_start_time = True
        invalid_end_date = True
        invalid_end_time = True

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

        # If user supplied either component, enforce equality
        if h_val is not None and h_val != implied_h:
            invalid_hours = True
        if m_val is not None and m_val != implied_m:
            invalid_minutes = True

    return (
        invalid_start_date,
        invalid_start_time,
        invalid_end_date,
        invalid_end_time,
        invalid_hours,
        invalid_minutes,
    )

def determine_missing_times(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    hours: str,
    minutes: str,
    validate: bool = False,
) -> tuple[int | None, datetime | None, datetime | None]:
    """
    Returns a tuple:
        (duration_minutes, start_dt, end_dt)
    where each value may be None if it cannot be computed.

    If validate=True and validation fails, all values are None.
    """

    # Optional validation
    if validate:
        (
            invalid_start_date,
            invalid_start_time,
            invalid_end_date,
            invalid_end_time,
            invalid_hours,
            invalid_minutes,
        ) = validate_time_inputs(
            start_date,
            start_time,
            end_date,
            end_time,
            hours,
            minutes,
        )

        if any(
            (
                invalid_start_date,
                invalid_start_time,
                invalid_end_date,
                invalid_end_time,
                invalid_hours,
                invalid_minutes,
            )
        ):
            return None, None, None

    # Normalize
    start_date = start_date or None
    start_time = start_time or None
    end_date = end_date or None
    end_time = end_time or None
    hours = hours or None
    minutes = minutes or None

    # Build datetime objects
    start_dt = combine_datetime(start_date, start_time)
    end_dt = combine_datetime(end_date, end_time)

    # Parse hours/minutes as ints
    h_val = None
    m_val = None

    if hours:
        try:
            h_val = int(hours)
        except Exception:
            pass

    if minutes:
        try:
            m_val = int(minutes)
        except Exception:
            pass

    duration_td: timedelta | None = None

    # Compute duration from timestamps
    if start_dt is not None and end_dt is not None and end_dt > start_dt:
        duration_td = end_dt - start_dt

    # If duration still unknown but components exist
    if duration_td is None and (h_val is not None or m_val is not None):
        total_minutes = 0
        if h_val is not None:
            total_minutes += h_val * 60
        if m_val is not None:
            total_minutes += m_val
        duration_td = timedelta(minutes=total_minutes)

    # Infer missing datetimes
    if start_dt is not None and duration_td is not None and end_dt is None:
        end_dt = start_dt + duration_td

    if end_dt is not None and duration_td is not None and start_dt is None:
        start_dt = end_dt - duration_td

    duration_minutes = None
    if duration_td is not None:
        duration_minutes = int(duration_td.total_seconds() // 60)

    return duration_minutes, start_dt, end_dt

# Validate date and time

def is_valid_date(date_str: str) -> bool:
    """Return True if date_str is a valid YYYY-MM-DD date."""
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except Exception:
        return False


def is_valid_time(time_str: str) -> bool:
    """Return True if time_str is a valid HH:MM time."""
    if not time_str or not isinstance(time_str, str):
        return False
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except Exception:
        return False


def combine_datetime(date_str: str, time_str: str):
    """Return a datetime if both parts are valid, else None."""
    if not (is_valid_date(date_str) and is_valid_time(time_str)):
        return None
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

# Category logic

def get_category_id_list(user_id: str) -> list[int]:
    """
    Return a list of active category IDs for the given user.
    """
    id_to_name = load_category_id_to_name(user_id)
    return list(id_to_name.keys())


def get_category_from_id(user_id: str, category_id: int) -> str | None:
    """
    Return the category name for a given active category_id owned by the user.
    Returns None if the category_id is not found (e.g., invalid, inactive, or not owned).
    """
    id_to_name = load_category_id_to_name(user_id)
    return id_to_name.get(int(category_id))


def get_category_layout(user_id, include_all_option=False):
    """
    Load categories from a JSON config file and return them as dropdown options.

    Args:
        config_path (str): Path to the JSON config file.
        include_all_option (bool): If True, includes an "All Categories" option at the top.

    Returns:

        List[dict]: Dropdown-compatible list of dictionaries with "label" and "value".
    """

    dropdown_options = load_category_list(user_id)

    if include_all_option:
        dropdown_options.insert(0, {"label": "All Categories", "value": "all"})

    return dropdown_options

# Formatting logic

def minutes_to_hmm(minutes):
    if minutes is None:
        return None
    try:
        minutes = int(round(minutes))
    except (TypeError, ValueError):
        return None

    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"

def fmt_h_m(mins: float) -> str:
    mins = int(round(mins))
    return f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"

def fmt_hh_mm(mins: float) -> str:
    mins = int(round(mins))
    hours = mins // 60
    mins_left = mins % 60
    return f"{hours}:{mins_left:02d}"


def fmt_int(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "0"
    return f"{int(round(value)):,}"