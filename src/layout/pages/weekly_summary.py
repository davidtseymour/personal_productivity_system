import dash_bootstrap_components as dbc
import pandas as pd
from dash import html

from src.logic.pages.weekly_summary import df_to_weekly_html_table
from src.data_access.db import (
    load_weekly_summary_minutes_by_day,
    load_weekly_summary_table_dailies,
)
from src.helpers.general import fmt_hh_mm, fmt_int


def _normalize_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure pivoted columns are `datetime.date` objects (not strings/Timestamps)."""
    out = df.copy()
    out.columns = pd.to_datetime(out.columns).date
    return out


def create_weekly_summary_page(user_id):
    # --- Tasks ---
    task_query = load_weekly_summary_minutes_by_day(user_id)
    task_summary = (
        task_query.pivot_table(
            index="category_name",
            columns="date",
            values="total_minutes",
            aggfunc="sum",
            fill_value=0,
        )
    )
    task_summary = _normalize_date_columns(task_summary)

    # --- Daily metrics ---
    daily_query = load_weekly_summary_table_dailies(user_id)
    daily_summary = (
        daily_query.pivot_table(
            index="display_name",
            columns="date",
            values="value_num",
            aggfunc="sum",
            fill_value=0,
        )
    )
    daily_summary = _normalize_date_columns(daily_summary)

    # --- Align date columns across both tables (union + sorted) ---
    all_dates = sorted(set(task_summary.columns).union(daily_summary.columns))
    task_summary = task_summary.reindex(columns=all_dates, fill_value=0)
    daily_summary = daily_summary.reindex(columns=all_dates, fill_value=0)

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Weekly Summary"), className="mb-2")),
            df_to_weekly_html_table(
                task_summary,
                daily_summary,
                fmt_hh_mm,
                fmt_int,
                highlight_rows={"Screen": {"color": "#b00020"}},
            ),
        ],
        fluid=True,
        className="p-0",
    )
