from datetime import date, timedelta

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.data_access.db import load_tasks_for_date_range
from src.helpers.general import get_category_layout
from src.layout.common_components import labeled_control_row
from src.layout.pages.daily_task_log import render_daily_task_log_table
from src.layout.shared_components.components import date_cycler_row


def create_task_explorer_page(user_id: str) -> dbc.Container:
    page = "task-explorer"
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    start_date_value = start_date.isoformat()
    end_date_value = end_date.isoformat()
    weekday_buttons = [
        ("dow-sun", "S"),
        ("dow-mon", "M"),
        ("dow-tue", "T"),
        ("dow-wed", "W"),
        ("dow-thu", "T"),
        ("dow-fri", "F"),
        ("dow-sat", "S"),
    ]
    task_rows = load_tasks_for_date_range(
        user_id=user_id,
        start_date=start_date_value,
        end_date=end_date_value,
    )

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Task Explorer")), className="mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            date_cycler_row(
                                page,
                                start_date_value,
                                date_name="start-date",
                                label_text="Start date",
                                prev_name="prev-start-day",
                                next_name="next-start-day",
                                prev_tooltip="Go to previous day",
                                next_tooltip="Go to next day",
                                row_class="g-2 align-items-center mb-2",
                            ),
                            date_cycler_row(
                                page,
                                end_date_value,
                                date_name="end-date",
                                label_text="End date",
                                prev_name="prev-end-day",
                                next_name="next-end-day",
                                prev_tooltip="Go to previous day",
                                next_tooltip="Go to next day",
                                row_class="g-2 align-items-center mb-0",
                            ),
                            html.Div(
                                [
                                    dbc.Label(
                                        "Days",
                                        className="mb-0",
                                        style={"width": "8.75rem", "flexShrink": 0},
                                    ),
                                    html.Div(
                                        [
                                            dbc.Button(
                                                label,
                                                id={"page": page, "name": day_name, "type": "button"},
                                                color="light",
                                                className="icon-action-btn task-explorer-weekday-btn",
                                                active=True,
                                                n_clicks=0,
                                            )
                                            for day_name, label in weekday_buttons
                                        ],
                                        style={
                                            "display": "flex",
                                            "gap": "0.5rem",
                                            "flexWrap": "wrap",
                                            "transform": "translateX(-20px)",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "0.5rem",
                                    "flexWrap": "wrap",
                                },
                                className="mt-2 mb-0",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            labeled_control_row(
                                "Category",
                                dcc.Dropdown(
                                    id={"page": page, "name": "category", "type": "dropdown"},
                                    options=get_category_layout(user_id, include_all_option=True),
                                    placeholder="Select category...",
                                    value="all",
                                ),
                                col_width=12,
                                className="mb-2",
                            ),
                            labeled_control_row(
                                "Subcategory",
                                [
                                    dbc.Input(
                                        id={"page": page, "name": "subcategory", "type": "input"},
                                        type="text",
                                        placeholder="Enter subcategory...",
                                        list="task-explorer-subcategory-suggestions",
                                        debounce=True,
                                    ),
                                    html.Datalist(
                                        id="task-explorer-subcategory-suggestions",
                                        children=[],
                                    ),
                                ],
                                col_width=12,
                                className="mb-2",
                            ),
                            labeled_control_row(
                                "Activity",
                                dbc.Input(
                                    id={"page": page, "name": "activity", "type": "input"},
                                    type="text",
                                    placeholder="Enter activity...",
                                    debounce=True,
                                ),
                                col_width=12,
                                className="mb-2",
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            render_daily_task_log_table(task_rows, table_page=page, show_date=True),
                            id={"page": page, "name": "task-table", "type": "table"},
                            style={
                                "minHeight": "28rem",
                                "maxHeight": "calc(100vh - 18rem)",
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
