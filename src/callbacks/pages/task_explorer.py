from datetime import date, timedelta

from dash import Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate
import pandas as pd

from src.data_access.db import load_tasks_for_date_range
from src.layout.pages.daily_task_log import render_daily_task_log_table


def register_task_explorer_callbacks(app: Dash) -> None:
    page = "task-explorer"
    weekday_map = [6, 0, 1, 2, 3, 4, 5]  # S, M, T, W, T, F, S -> Python weekday ints

    @app.callback(
        Output({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-start-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-start-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_task_explorer_start_date(
        _prev_clicks,
        _next_clicks,
        start_date_value,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            start_dt = date.fromisoformat(start_date_value) if start_date_value else date.today()
        except (TypeError, ValueError):
            start_dt = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-start-day":
            delta = -1
        elif source_name == "next-start-day":
            delta = 1
        else:
            raise PreventUpdate

        return (start_dt + timedelta(days=delta)).isoformat()

    @app.callback(
        Output({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-end-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-end-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_task_explorer_end_date(
        _prev_clicks,
        _next_clicks,
        end_date_value,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            end_dt = date.fromisoformat(end_date_value) if end_date_value else date.today()
        except (TypeError, ValueError):
            end_dt = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-end-day":
            delta = -1
        elif source_name == "next-end-day":
            delta = 1
        else:
            raise PreventUpdate

        return (end_dt + timedelta(days=delta)).isoformat()

    @app.callback(
        Output({"page": page, "name": "dow-sun", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-mon", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-tue", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-wed", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-thu", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-fri", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-sat", "type": "button"}, "active"),
        Input({"page": page, "name": "dow-sun", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-mon", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-tue", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-wed", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-thu", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-fri", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-sat", "type": "button"}, "n_clicks"),
    )
    def update_weekday_button_state(*weekday_clicks):
        return [((clicks or 0) % 2 == 0) for clicks in weekday_clicks]

    @app.callback(
        Output({"page": page, "name": "task-table", "type": "table"}, "children"),
        Input({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "category", "type": "dropdown"}, "value"),
        Input({"page": page, "name": "subcategory", "type": "input"}, "value"),
        Input({"page": page, "name": "activity", "type": "input"}, "value"),
        Input({"page": page, "name": "dow-sun", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-mon", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-tue", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-wed", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-thu", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-fri", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-sat", "type": "button"}, "n_clicks"),
        Input("user-id", "data"),
        Input("task-nav-update-store", "data"),
        Input("last-update", "data"),
    )
    def update_task_explorer_table(
        start_date_value,
        end_date_value,
        category_value,
        subcategory_filter,
        activity_filter,
        n_sun,
        n_mon,
        n_tue,
        n_wed,
        n_thu,
        n_fri,
        n_sat,
        user_id,
        _task_reload,
        _last_update,
    ):
        if not user_id or not start_date_value or not end_date_value:
            raise PreventUpdate

        weekday_clicks = [n_sun, n_mon, n_tue, n_wed, n_thu, n_fri, n_sat]
        selected_weekdays = {
            weekday_map[idx]
            for idx, clicks in enumerate(weekday_clicks)
            if (clicks or 0) % 2 == 0
        }

        if not selected_weekdays:
            return render_daily_task_log_table(None, table_page=page, show_date=True)

        try:
            start_dt = date.fromisoformat(start_date_value)
            end_dt = date.fromisoformat(end_date_value)
        except (TypeError, ValueError):
            raise PreventUpdate

        range_start = min(start_dt, end_dt).isoformat()
        range_end = max(start_dt, end_dt).isoformat()

        task_rows = load_tasks_for_date_range(
            user_id=user_id,
            start_date=range_start,
            end_date=range_end,
        )
        if task_rows is None or task_rows.empty:
            return render_daily_task_log_table(task_rows, table_page=page, show_date=True)

        filtered = task_rows.copy()
        weekday_values = pd.to_datetime(filtered["date"], errors="coerce").dt.weekday
        filtered = filtered[weekday_values.isin(selected_weekdays)].copy()

        if filtered.empty:
            return render_daily_task_log_table(filtered, table_page=page, show_date=True)

        if category_value not in (None, "", "all"):
            try:
                filtered = filtered[filtered["category_id"] == int(category_value)].copy()
            except (TypeError, ValueError):
                pass

        subcategory_query = (subcategory_filter or "").strip()
        if subcategory_query:
            filtered = filtered[
                filtered["subcategory"].fillna("").astype(str).str.contains(
                    subcategory_query, case=False, regex=False
                )
            ].copy()

        activity_query = (activity_filter or "").strip()
        if activity_query:
            filtered = filtered[
                filtered["activity"].fillna("").astype(str).str.contains(
                    activity_query, case=False, regex=False
                )
            ].copy()

        # Keep broad case-insensitive filtering, but rank exact-case matches first.
        case_rank = 0
        if subcategory_query:
            subcat_case_match = filtered["subcategory"].fillna("").astype(str).str.contains(
                subcategory_query, case=True, regex=False
            )
            case_rank = case_rank + subcat_case_match.astype(int)
        if activity_query:
            activity_case_match = filtered["activity"].fillna("").astype(str).str.contains(
                activity_query, case=True, regex=False
            )
            case_rank = case_rank + activity_case_match.astype(int)

        if subcategory_query or activity_query:
            filtered = filtered.copy()
            filtered["_case_rank"] = case_rank
            filtered["_base_order"] = range(len(filtered))
            filtered = filtered.sort_values(
                by=["_case_rank", "_base_order"],
                ascending=[False, True],
                kind="mergesort",
            ).drop(columns=["_case_rank", "_base_order"])

        return render_daily_task_log_table(filtered, table_page=page, show_date=True)
