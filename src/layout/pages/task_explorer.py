from datetime import date, timedelta

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.data_access.db import load_tasks_for_date_range
from src.helpers.general import get_category_layout
from src.layout.common_components import create_toast, labeled_control_row
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
            dcc.Store(id={"page": page, "name": "filtered-task-snapshot", "type": "store"}, data=[]),
            dcc.Store(id={"page": page, "name": "bulk-edit-pending", "type": "store"}, data={}),
            dcc.Store(id={"page": page, "name": "bulk-edit-refresh", "type": "store"}, data=""),
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
                            dbc.Row(
                                dbc.Col(
                                    dbc.Button(
                                        "Bulk Edit",
                                        id={"page": page, "name": "open-bulk-edit", "type": "button"},
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                    ),
                                    width="auto",
                                ),
                                className="g-0",
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
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Bulk Edit Tasks")),
                    dbc.ModalBody(
                        [
                            html.Div(
                                "Apply updates to the currently filtered task set.",
                                className="text-muted small mb-2",
                            ),
                            dbc.Row(
                                dbc.Col(
                                    html.Div("Direct Match (Case Sensitive)", className="fw-semibold"),
                                    width=12,
                                ),
                                className="mb-2",
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Category",
                                        dcc.Dropdown(
                                            id={"page": page, "name": "bulk-match-category", "type": "dropdown"},
                                            options=get_category_layout(user_id, include_all_option=True),
                                            value="all",
                                            clearable=False,
                                        ),
                                        col_width=12,
                                        className="mb-2",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Subcategory",
                                        dbc.Input(
                                            id={"page": page, "name": "bulk-match-subcategory", "type": "input"},
                                            type="text",
                                            placeholder="Exact subcategory match",
                                        ),
                                        col_width=12,
                                        className="mb-2",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Activity",
                                        dbc.Input(
                                            id={"page": page, "name": "bulk-match-activity", "type": "input"},
                                            type="text",
                                            placeholder="Exact activity match",
                                        ),
                                        col_width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                dbc.Col(
                                    html.Div("Set New Values", className="fw-semibold"),
                                    width=12,
                                ),
                                className="mb-2",
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Category",
                                        dcc.Dropdown(
                                            id={"page": page, "name": "bulk-set-category", "type": "dropdown"},
                                            options=get_category_layout(user_id, include_all_option=False),
                                            placeholder="Leave unchanged",
                                        ),
                                        col_width=12,
                                        className="mb-2",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Subcategory",
                                        dbc.Input(
                                            id={"page": page, "name": "bulk-set-subcategory", "type": "input"},
                                            type="text",
                                            placeholder="Leave unchanged",
                                        ),
                                        col_width=12,
                                        className="mb-2",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Activity",
                                        dbc.Input(
                                            id={"page": page, "name": "bulk-set-activity", "type": "input"},
                                            type="text",
                                            placeholder="Leave unchanged",
                                        ),
                                        col_width=12,
                                        className="mb-2",
                                    ),
                                ]
                            ),
                            html.Small(
                                "",
                                id={"page": page, "name": "bulk-edit-error", "type": "text"},
                                className="text-danger",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id={"page": page, "name": "cancel-bulk-edit", "type": "button"},
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Review Changes",
                                id={"page": page, "name": "review-bulk-edit", "type": "button"},
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id={"page": page, "name": "bulk-edit-modal", "type": "modal"},
                is_open=False,
                size="lg",
                backdrop="static",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Confirm Bulk Edit")),
                    dbc.ModalBody(
                        html.Div(
                            id={"page": page, "name": "bulk-edit-confirm-summary", "type": "text"},
                            className="small",
                        )
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Back",
                                id={"page": page, "name": "cancel-bulk-confirm", "type": "button"},
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Apply Bulk Edit",
                                id={"page": page, "name": "confirm-bulk-edit", "type": "button"},
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id={"page": page, "name": "bulk-edit-confirm-modal", "type": "modal"},
                is_open=False,
                backdrop="static",
            ),
            create_toast(page, "bulk-edit", "Task Explorer", icon="success"),
        ],
        fluid=True,
        className="p-0",
    )
