import dash_bootstrap_components as dbc
from dash import dcc, html

from src.data_access.goals import get_goals_themes
from src.layout.common_components import create_toast, labeled_control_row


def create_goals(user_id: str) -> dbc.Container:
    page = "goals"

    return dbc.Container(
        [
            html.H5("Goals"),
            dbc.Row(
                [
                    dcc.Store(id="goals-last-saved-store"),
                    labeled_control_row(
                        "Theme",
                        dcc.Dropdown(
                            id={"page": page, "name": "goal-theme", "type": "dropdown"},
                            options=get_goals_themes(user_id),
                            placeholder="Select goal theme...",
                        ),
                        col_width=4,
                        label_px=110,
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
                                className="rounded-circle ms-2",
                                style={
                                    "width": "32px",
                                    "height": "32px",
                                    "padding": "0",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "marginTop": "0.2rem",  # tweak to align with dropdown
                                },
                            ),
                            dbc.Tooltip(
                                "Add goal theme",
                                target={"page": page, "name": "open-add-goal-theme", "type": "button"},
                                placement="right",
                            ),
                        ],
                        width="auto",
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("This quarter's goals"),
                            dbc.Textarea(
                                id={"page": page, "name": "three-month-goals", "type": "textarea"},
                                placeholder="What are your goals for this quarter?",
                                style={"minHeight": "140px"},
                            ),
                        ],
                        width=8,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("This month's goals"),
                            dbc.Textarea(
                                id={"page": page, "name": "one-month-goals", "type": "textarea"},
                                placeholder="What are your goals for this month?",
                                style={"minHeight": "140px"},
                            ),
                        ],
                        width=8,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("This week's goals"),
                            dbc.Textarea(
                                id={"page": page, "name": "this-weeks-goals", "type": "textarea"},
                                placeholder="What are your goals for this week?",
                                style={"minHeight": "180px"},
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Last week's goals"),
                            dbc.Textarea(
                                id={"page": page, "name": "last-weeks-goals", "type": "textarea"},
                                style={"minHeight": "180px"},
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mb-3",
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
                                            placeholder="Short label, e.g., Fitness, Career…",
                                            autoComplete="off",
                                            autoFocus=True,
                                        ),
                                        col_width=12,
                                        label_px=110,
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
            create_toast(page, "goals", "Load Goals", icon="success"),
            create_toast(page, "save-goals", "Save Goals", icon="success"),
        ],
        fluid=True,
        className="p-0",
    )
