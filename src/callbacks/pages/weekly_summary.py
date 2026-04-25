from datetime import date, timedelta

from dash import Input, Output, State, ctx
from dash.exceptions import PreventUpdate
import pandas as pd

from src.data_access.db import (
    load_weekly_summary_minutes_by_day,
    load_weekly_summary_table_dailies,
)
from src.helpers.general import fmt_hh_mm, fmt_int
from src.logic.pages.weekly_summary import df_to_weekly_html_table


def _normalize_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = pd.to_datetime(out.columns).date
    return out


def register_weekly_summary_callbacks(app):
    page = "weekly-summary"

    @app.callback(
        Output({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-week", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-week", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_weekly_summary_date(_prev_clicks, _next_clicks, selected_date):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            base_date = date.fromisoformat(selected_date) if selected_date else (date.today() - timedelta(days=7))
        except (TypeError, ValueError):
            base_date = date.today() - timedelta(days=7)

        source_name = triggered.get("name")
        if source_name == "prev-week":
            return (base_date - timedelta(days=7)).isoformat()
        if source_name == "next-week":
            return (base_date + timedelta(days=7)).isoformat()

        raise PreventUpdate

    @app.callback(
        Output({"page": page, "name": "weekly-table", "type": "table"}, "children"),
        Input({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input("user-id", "data"),
        Input("last-update", "data"),
        prevent_initial_call=True,
    )
    def update_weekly_summary(selected_date, user_id, _last_update):
        if not user_id or not selected_date:
            raise PreventUpdate

        try:
            selected_start_date = date.fromisoformat(selected_date)
        except (TypeError, ValueError):
            raise PreventUpdate

        task_query = load_weekly_summary_minutes_by_day(
            user_id, selected_start_date=selected_start_date
        )
        task_summary = task_query.pivot_table(
            index="category_name",
            columns="date",
            values="total_minutes",
            aggfunc="sum",
            fill_value=0,
        )
        task_summary = _normalize_date_columns(task_summary)

        daily_query = load_weekly_summary_table_dailies(
            user_id, selected_start_date=selected_start_date
        )
        daily_summary = daily_query.pivot_table(
            index="display_name",
            columns="date",
            values="value_num",
            aggfunc="sum",
            fill_value=0,
        )
        daily_summary = _normalize_date_columns(daily_summary)

        all_dates = sorted(set(task_summary.columns).union(daily_summary.columns))
        task_summary = task_summary.reindex(columns=all_dates, fill_value=0)
        daily_summary = daily_summary.reindex(columns=all_dates, fill_value=0)

        return df_to_weekly_html_table(
            task_summary,
            daily_summary,
            fmt_hh_mm,
            fmt_int,
            highlight_rows={"Screen": {"color": "#b00020"}},
        )
