from datetime import date

from dash import html
import dash_bootstrap_components as dbc
import pandas as pd

from src.data_access.db import load_tasks_for_day
from src.layout.shared_components.components import date_cycler_row


def _fmt_time(value: object) -> str:
    if value is None:
        return ""
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return ""
    return timestamp.strftime("%-I:%M %p")


def _fmt_duration(value: object) -> str:
    if value is None:
        return ""
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return ""
    hours = minutes // 60
    mins_left = minutes % 60
    if hours <= 0:
        return f"{mins_left}m"
    return f"{hours}h {mins_left:02d}m"


def render_daily_task_log_table(task_rows: pd.DataFrame | None) -> dbc.Table | html.Small:
    if task_rows is None or task_rows.empty:
        return html.Small("No tasks logged for the selected day.", className="text-muted px-2")

    header = html.Thead(
        html.Tr(
            [
                html.Th("Start", style={"width": "88px"}),
                html.Th("End", style={"width": "88px"}),
                html.Th("Duration", className="text-end", style={"width": "88px", "paddingRight": "1rem"}),
                html.Th("Category", style={"paddingLeft": "1rem"}),
                html.Th("Subcategory"),
                html.Th("Activity"),
                html.Th("Notes"),
                html.Th("Actions", className="text-center align-middle", style={"width": "72px"}),
            ]
        ),
    )

    body = html.Tbody(
        [
            html.Tr(
                [
                    html.Td(_fmt_time(row.get("start_at")), className="text-muted small"),
                    html.Td(_fmt_time(row.get("end_at")), className="text-muted small"),
                    html.Td(
                        _fmt_duration(row.get("duration_min")),
                        className="text-end small",
                        style={"paddingRight": "1rem"},
                    ),
                    html.Td((row.get("category") or ""), className="small", style={"paddingLeft": "1rem"}),
                    html.Td((row.get("subcategory") or ""), className="small"),
                    html.Td((row.get("activity") or ""), className="small"),
                    html.Td((row.get("notes") or ""), className="small text-muted"),
                    html.Td(
                        html.Div(
                            [
                                dbc.Button(
                                    html.I(className="bi bi-pencil"),
                                    id={
                                        "page": "daily-task-log",
                                        "type": "edit-task",
                                        "task_id": int(row.get("task_id")),
                                    },
                                    className="icon-action-btn daily-task-log-row-action me-1",
                                    title="Edit task",
                                    n_clicks=0,
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-trash"),
                                    id={
                                        "page": "daily-task-log",
                                        "type": "delete-task",
                                        "task_id": int(row.get("task_id")),
                                    },
                                    className="icon-action-btn daily-task-log-row-action",
                                    title="Delete task",
                                    n_clicks=0,
                                ),
                            ],
                            className="d-flex justify-content-center align-items-center",
                        ),
                        className="text-center align-middle",
                    ),
                ]
            )
            for _, row in task_rows.iterrows()
        ]
    )

    return dbc.Table(
        [header, body],
        bordered=False,
        hover=True,
        size="sm",
        className="daily-summary-table daily-task-log-table mb-0 align-middle",
        responsive=True,
    )


def create_daily_task_log_page(user_id: str) -> dbc.Container:
    page = "daily-task-log"
    selected_date = date.today().isoformat()
    task_rows = load_tasks_for_day(user_id=user_id, selected_date=selected_date)

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Task Log")), className="mb-2"),
            date_cycler_row(
                page,
                selected_date,
                prev_name="prev-day",
                next_name="next-day",
                prev_tooltip="Go to previous day",
                next_tooltip="Go to next day",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            render_daily_task_log_table(task_rows),
                            id={"page": page, "name": "task-table", "type": "table"},
                            style={
                                "minHeight": "28rem",
                                "maxHeight": "calc(100vh - 14rem)",
                                "overflowY": "auto",
                            },
                        ),
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
        ],
        fluid=True,
        className="p-0",
    )
