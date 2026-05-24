from datetime import date

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.data_access.goals import get_goals_themes
from src.layout.common_components import create_toast, labeled_control_row
from src.layout.shared_components.components import date_cycler_row, labeled_fixed_width_control_row


def _goal_section(
    page: str,
    *,
    horizon: str,
) -> dbc.Row:
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        id={"page": page, "name": "goal-items-container", "type": "container", "horizon": horizon},
                        className="goals-table-region",
                    ),
                ],
                width=12,
            ),
        ],
        className="mb-4 goals-section",
    )


def create_goals(user_id: str) -> dbc.Container:
    page = "goals"
    selected_date = date.today().isoformat()

    return dbc.Container(
        [
            dcc.Store(id="goals-items-store", data={}),
            dcc.Store(id="goal-item-settings-target-store", data={}),
            dbc.Row(dbc.Col(html.H5("Goals"), width=12), className="mb-2"),
            date_cycler_row(
                page,
                selected_date,
                prev_name="prev-week",
                next_name="next-week",
                prev_tooltip="Go to previous week",
                next_tooltip="Go to next week",
            ),
            dbc.Row(
                [
                    labeled_fixed_width_control_row(
                        "Theme",
                        dcc.Dropdown(
                            id={"page": page, "name": "goal-theme", "type": "dropdown"},
                            options=get_goals_themes(user_id),
                            placeholder="Select goal theme",
                            style={"width": "100%"},
                        ),
                        control_width="12.375rem",
                        col_width="auto",
                        label_width="5.25rem",
                        className="mb-0",
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                html.I(
                                    className="bi bi-plus-lg",
                                    style={"fontSize": "1.2rem"},
                                ),
                                id={"page": page, "name": "open-add-goal-theme", "type": "button"},
                                color="light",
                                size="sm",
                                className="rounded-circle",
                                style={
                                    "width": "28px",
                                    "height": "28px",
                                    "padding": "0",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                },
                            ),
                            dbc.Tooltip(
                                "Add goal theme",
                                target={"page": page, "name": "open-add-goal-theme", "type": "button"},
                                placement="right",
                            ),
                        ],
                        width="auto",
                        className="d-flex align-items-center justify-content-end",
                        style={"width": "2.5rem", "flexShrink": 0},
                    ),
                ],
                className="g-2 align-items-center mb-3",
            ),
            _goal_section(
                page,
                horizon="QTR",
            ),
            _goal_section(
                page,
                horizon="MONTH",
            ),
            _goal_section(
                page,
                horizon="WEEK",
            ),
            _goal_section(
                page,
                horizon="WEEK_MINUS_1",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            "Update Goals",
                            id={"page": page, "name": "update-goals", "type": "button"},
                            className="me-2",
                        ),
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Modal(
                [
                    dbc.ModalBody(
                        [
                            html.H5("Add Theme"),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Theme",
                                        dbc.Input(
                                            id={"page": page, "name": "new-theme-name", "type": "input"},
                                            type="text",
                                            placeholder="Short label, e.g., Fitness, Career",
                                            autoComplete="off",
                                            autoFocus=True,
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Alert(
                                                id={"page": page, "name": "new-theme-error", "type": "alert"},
                                                color="danger",
                                                is_open=False,
                                                className="mt-2 mb-0",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id={"page": page, "name": "cancel-add-theme", "type": "button"},
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        "Add Theme",
                                        id={"page": page, "name": "save-add-theme", "type": "button"},
                                        color="primary",
                                        className="me-2",
                                    ),
                                ],
                                className="d-flex justify-content-end",
                            ),
                        ]
                    )
                ],
                id={"page": page, "name": "add-theme-modal", "type": "modal"},
                is_open=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id={"page": page, "name": "goal-item-settings-title", "type": "text"})),
                    dbc.ModalBody(
                        [
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Progress",
                                        dbc.Select(
                                            id={"page": page, "name": "goal-item-settings-progress-mode", "type": "input"},
                                            options=[
                                                {"label": "Manual", "value": "MANUAL"},
                                                {"label": "Auto from Time", "value": "AUTO_TIME"},
                                            ],
                                            value="MANUAL",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Source",
                                        dbc.Select(
                                            id={"page": page, "name": "goal-item-settings-calc-source", "type": "input"},
                                            options=[
                                                {"label": "Tasks", "value": "TASKS"},
                                                {"label": "Metrics", "value": "METRICS"},
                                                {"label": "Tasks + Metrics", "value": "TASKS_AND_METRICS"},
                                            ],
                                            value="TASKS_AND_METRICS",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Standard",
                                        dbc.Select(
                                            id={"page": page, "name": "goal-item-settings-target-scope", "type": "input"},
                                            options=[
                                                {"label": "Per Day", "value": "DAY"},
                                                {"label": "Per Period", "value": "PERIOD"},
                                            ],
                                            value="PERIOD",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Operator",
                                        dbc.Select(
                                            id={"page": page, "name": "goal-item-settings-target-operator", "type": "input"},
                                            options=[
                                                {"label": "At Least", "value": "GTE"},
                                                {"label": "At Most", "value": "LTE"},
                                            ],
                                            value="GTE",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Target Min",
                                        dbc.Input(
                                            id={"page": page, "name": "goal-item-settings-target-minutes", "type": "input"},
                                            type="text",
                                            inputMode="decimal",
                                            pattern="^\\d*(?:\\.\\d+)?$",
                                            placeholder="Optional",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Category",
                                        dbc.Select(
                                            id={"page": page, "name": "goal-item-settings-category", "type": "input"},
                                            options=[{"label": "Unassigned", "value": ""}],
                                            value="",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Subcategory",
                                        dbc.Input(
                                            id={"page": page, "name": "goal-item-settings-subcategory", "type": "input"},
                                            type="text",
                                            placeholder="Optional",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Activity",
                                        dbc.Input(
                                            id={"page": page, "name": "goal-item-settings-activity", "type": "input"},
                                            type="text",
                                            placeholder="Optional",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Weight",
                                        dbc.Input(
                                            id={"page": page, "name": "goal-item-settings-weight", "type": "input"},
                                            type="text",
                                            inputMode="decimal",
                                            pattern="^(?:0*\\.[0-9]*[1-9][0-9]*|[1-9][0-9]*(?:\\.\\d+)?)$",
                                            value=1.0,
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    labeled_control_row(
                                        "Notes",
                                        dbc.Textarea(
                                            id={"page": page, "name": "goal-item-settings-notes", "type": "input"},
                                            rows=4,
                                            placeholder="Optional",
                                        ),
                                        col_width=12,
                                        label_width="6.875rem",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Alert(
                                            id={"page": page, "name": "goal-item-settings-assessment", "type": "alert"},
                                            color="secondary",
                                            className="mt-2 mb-0 py-2",
                                            is_open=True,
                                        ),
                                        width=12,
                                    )
                                ]
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id={"page": page, "name": "cancel-goal-item-settings", "type": "button"},
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Save",
                                id={"page": page, "name": "save-goal-item-settings", "type": "button"},
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id={"page": page, "name": "goal-item-settings-modal", "type": "modal"},
                is_open=False,
                size="lg",
            ),
            create_toast(page, "goals", "Load Goals", icon="success"),
            create_toast(page, "save-goals", "Save Goals", icon="success"),
        ],
        fluid=True,
        className="p-0",
    )
