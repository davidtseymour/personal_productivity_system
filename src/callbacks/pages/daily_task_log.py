from datetime import date, timedelta

from dash import Dash, Input, Output, State, ctx
from dash.exceptions import PreventUpdate

from src.data_access.db import load_tasks_for_day
from src.layout.pages.daily_task_log import render_daily_task_log_table


def register_daily_task_log_callbacks(app: Dash) -> None:
    page = "daily-task-log"

    @app.callback(
        Output({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_daily_task_log_date(_prev_clicks, _next_clicks, selected_date):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            base_date = date.fromisoformat(selected_date) if selected_date else date.today()
        except (TypeError, ValueError):
            base_date = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-day":
            return (base_date - timedelta(days=1)).isoformat()
        if source_name == "next-day":
            return (base_date + timedelta(days=1)).isoformat()

        raise PreventUpdate

    @app.callback(
        Output({"page": page, "name": "task-table", "type": "table"}, "children"),
        Input({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input("user-id", "data"),
        Input("task-nav-update-store", "data"),
        Input("last-update", "data"),
    )
    def update_daily_task_log_table(selected_date, user_id, _task_reload, _last_update):
        if not user_id or not selected_date:
            raise PreventUpdate

        task_rows = load_tasks_for_day(user_id=user_id, selected_date=selected_date)
        return render_daily_task_log_table(task_rows)
