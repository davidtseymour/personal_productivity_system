from datetime import date

from dash import html
import dash_bootstrap_components as dbc

from src.layout.common_components import create_toast
from src.layout.shared_components.components import date_cycler_row, labeled_fixed_width_control_row


def create_daily_reflection() -> dbc.Container:
    page = "daily-reflection"
    selected_date = date.today().isoformat()

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Reflection")), className="mb-2"),
            date_cycler_row(
                page,
                selected_date,
                prev_name="prev-day",
                next_name="next-day",
                prev_tooltip="Go to previous day",
                next_tooltip="Go to next day",
            ),
            labeled_fixed_width_control_row(
                "Intentionality Score",
                dbc.Input(
                    id={"page": page, "name": "intentionality-score", "type": "input"},
                    type="number",
                    min=1,
                    max=10,
                    step=1,
                    placeholder="1-10",
                    style={"width": "5rem", "textAlign": "right", "marginLeft": "auto"},
                    autoComplete="off",
                    debounce=True,
                ),
                col_width=12,
                control_width="8.75rem",
                label_width="8.75rem",
                className="mb-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Accomplishments"),
                            dbc.Textarea(
                                id={"page": page, "name": "accomplishments", "type": "textarea"},
                                placeholder="Big wins, progress, or anything worth noting today.",
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
                            dbc.Label("What worked"),
                            dbc.Textarea(
                                id={"page": page, "name": "what-worked", "type": "textarea"},
                                placeholder="What helped things go well?",
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
                            dbc.Label("What didn’t work"),
                            dbc.Textarea(
                                id={"page": page, "name": "what-didnt-work", "type": "textarea"},
                                placeholder="What got in the way or didn’t go as planned?",
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
                            dbc.Label("Intentions for tomorrow"),
                            dbc.Textarea(
                                id={"page": page, "name": "intentions-tomorrow", "type": "textarea"},
                                placeholder="What would make tomorrow feel successful?",
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
                        dbc.Button(
                            "Submit Reflection",
                            id={"page": page, "name": "submit", "type": "button"},
                            className="me-2",
                        ),
                        width=4,
                    ),
                ],
                className="mb-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        html.Div(id={"page": page, "name": "output", "type": "div"}),
                        width=8,
                    ),
                ]
            ),

            create_toast(page, "save-reflection", "Daily Reflection", icon="success"),
            create_toast(page, "load-reflection", "Daily Reflection", icon="info"),
        ],
        fluid=True,
        className="p-0",
    )
