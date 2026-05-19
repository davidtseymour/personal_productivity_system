from datetime import date, timedelta

import pandas as pd

from src.data_access.db import load_tasks_for_date_range

TIMELINE_TASK_COLUMNS = [
    "task_id",
    "category_id",
    "category",
    "subcategory",
    "activity",
    "start_at",
    "end_at",
    "duration_min",
]


def _empty_timeline_df() -> pd.DataFrame:
    return pd.DataFrame(columns=TIMELINE_TASK_COLUMNS)


def _normalize_summary_date(summary_date: str | date) -> date:
    if isinstance(summary_date, date):
        return summary_date

    parsed = pd.to_datetime(summary_date, errors="coerce")
    if pd.isna(parsed):
        raise ValueError("Invalid summary_date")
    return parsed.date()


def load_timeline_tasks_for_date(user_id: str, summary_date: str | date) -> pd.DataFrame:
    """
    Load task rows relevant to a selected day and normalize core timeline fields.

    This intentionally queries a 3-day window [day-1, day+1] so cross-midnight tasks
    that intersect the selected day can be included before clipping in timeline logic.
    """
    if not user_id:
        return _empty_timeline_df()

    try:
        selected_date = _normalize_summary_date(summary_date)
    except ValueError:
        return _empty_timeline_df()

    start_date = selected_date - timedelta(days=1)
    end_date = selected_date + timedelta(days=1)

    task_rows = load_tasks_for_date_range(user_id, start_date=start_date, end_date=end_date)
    if task_rows is None or task_rows.empty:
        return _empty_timeline_df()

    df = task_rows.copy()

    for column in TIMELINE_TASK_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df["start_at"] = pd.to_datetime(df["start_at"], errors="coerce")
    df["end_at"] = pd.to_datetime(df["end_at"], errors="coerce")
    df = df.dropna(subset=["start_at", "end_at"])
    df = df[df["end_at"] > df["start_at"]].copy()

    if df.empty:
        return _empty_timeline_df()

    df["task_id"] = pd.to_numeric(df["task_id"], errors="coerce")
    df = df.dropna(subset=["task_id"])
    if df.empty:
        return _empty_timeline_df()
    df["task_id"] = df["task_id"].astype(int)

    df["category_id"] = pd.to_numeric(df["category_id"], errors="coerce").astype("Int64")
    df["category"] = df["category"].fillna("Uncategorized").astype(str)
    df["subcategory"] = df["subcategory"].fillna("").astype(str)
    df["activity"] = df["activity"].fillna("").astype(str)

    raw_duration = pd.to_numeric(df["duration_min"], errors="coerce")
    computed_duration = (df["end_at"] - df["start_at"]).dt.total_seconds() / 60
    df["duration_min"] = raw_duration.fillna(computed_duration).fillna(0).round().astype(int)

    return (
        df[TIMELINE_TASK_COLUMNS]
        .sort_values(["start_at", "end_at", "task_id"])
        .reset_index(drop=True)
    )
