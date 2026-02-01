from datetime import date, datetime, timedelta
from typing import Literal

from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

from src.data_access.goals import get_goal_set_id, create_and_get_goal_set_id

GoalHorizon = Literal["WEEK", "MONTH", "QTR"]

def _start_of_week(d: date, week_start: int = 0) -> date:
    """
    week_start: 0=Monday, 6=Sunday (Python's date.weekday(): Mon=0...Sun=6)
    """
    if not (0 <= week_start <= 6):
        raise ValueError("week_start must be in [0..6] where 0=Monday, 6=Sunday.")
    delta = (d.weekday() - week_start) % 7
    return d - timedelta(days=delta)


def _start_of_month(d: date) -> date:
    return d.replace(day=1)


def _start_of_quarter(d: date) -> date:
    first_month = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, first_month, 1)


def compute_period_start(
    horizon: GoalHorizon,
    offset: int = 0,
    tz: str = "America/New_York",
    week_start: int = 0,  # Monday week start
    now_dt: datetime | None = None,
) -> date:
    """
    Compute the period start date in the user's timezone.

    offset:
      WEEK  -> +/- N weeks
      MONTH -> +/- N months
      QTR   -> +/- N quarters
    """
    tzinfo = ZoneInfo(tz)
    local_now = (now_dt or datetime.now(tzinfo)).astimezone(tzinfo)
    today = local_now.date()

    if horizon == "WEEK":
        base = _start_of_week(today, week_start=week_start)
        return base + timedelta(days=7 * offset)

    if horizon == "MONTH":
        base = _start_of_month(today)
        return base + relativedelta(months=+offset)

    if horizon == "QTR":
        base = _start_of_quarter(today)
        return base + relativedelta(months=+(3 * offset))

    # Should be unreachable if GoalHorizon typing is respected.
    raise AssertionError(f"Unhandled horizon: {horizon!r}")


def get_goal_set_id_for_offset(
    user_id: str,
    horizon: GoalHorizon,
    offset: int = 0,
    tz: str = "America/New_York",
    week_start: int = 0,
    now_dt: datetime | None = None,
) -> tuple[int | None, date]:
    """
    Compute period_start for the given horizon/offset and return (goal_set_id, period_start_date).
    """
    if user_id is None:
        raise ValueError("user_id is required")
    user_id = str(user_id)

    period_start = compute_period_start(
        horizon=horizon,
        offset=offset,
        tz=tz,
        week_start=week_start,
        now_dt=now_dt,
    )
    goal_set_id = get_goal_set_id(user_id, horizon, period_start)
    return goal_set_id, period_start


def ensure_goal_set_id_for_save(
    *,
    user_id: str,
    horizon: GoalHorizon,
    offset: int = 0,
    tz: str = "America/New_York",
    week_start: int = 0,
    now_dt: datetime | None = None,
) -> int:
    """
    Ensure a goal_set row exists for (user_id, horizon, computed period_start) and return its id.

    period_start is computed via `compute_period_start(...)` using:
      - horizon
      - offset (0=current period, -1=previous, +1=next, etc.)
      - tz / week_start / now_dt (passed through for deterministic testing and week alignment)

    Behavior:
      - Computes period_start for the requested horizon/offset
      - Looks up an existing goal_set_id for (user_id, horizon, period_start)
      - Creates the goal_set row if missing
      - Returns the existing or newly-created goal_set_id
    """
    if user_id is None:
        raise ValueError("user_id is required")
    user_id = str(user_id)

    period_start = compute_period_start(
        horizon=horizon,
        offset=offset,
        tz=tz,
        week_start=week_start,
        now_dt=now_dt,
    )

    existing_id = get_goal_set_id(user_id, horizon, period_start)
    if existing_id is not None:
        return existing_id

    created_id = create_and_get_goal_set_id(
        user_id=user_id,
        horizon=horizon,
        period_start=period_start,
    )
    return created_id