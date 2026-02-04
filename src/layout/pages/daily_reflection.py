from datetime import date

import dash_bootstrap_components as dbc
from dash import html

from src.layout.common_components import create_toast


def create_daily_review() -> dbc.Container:
    page = "daily-review"

    return dbc.Container(
        [
            html.H5("Daily Reflection"),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Date"),
                            dbc.Input(
                                id={"page": page, "name": "date", "type": "date-input"},
                                type="date",
                                value=date.today().isoformat(),
                                placeholder="Date",
                            ),
                        ],
                        width=4,
                    ),

                    dbc.Col(
                        [
                            dbc.Label("Intentionality Score (1–10)"),
                            dbc.Input(
                                id={"page": page, "name": "intentionality-score", "type": "input"},
                                type="number",
                                min=1,
                                max=10,
                                style={"width": "80px"},
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
                        [
                            dbc.Label("Accomplishments"),
                            dbc.Textarea(
                                id={"page": page, "name": "accomplishments", "type": "textarea"},
                                placeholder="What did you accomplish today?",
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
                            dbc.Label("What Worked"),
                            dbc.Textarea(
                                id={"page": page, "name": "what-worked", "type": "textarea"},
                                placeholder="What went well?",
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
                            dbc.Label("What Didn't Work"),
                            dbc.Textarea(
                                id={"page": page, "name": "what-didnt-work", "type": "textarea"},
                                placeholder="What didn't go well?",
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
                            dbc.Label("One Thing to Improve"),
                            dbc.Textarea(
                                id={"page": page, "name": "improve-one-thing", "type": "textarea"},
                                placeholder="What will you do differently?",
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
                            "Submit Review",
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

            create_toast(page, "save-review", "Daily Reflection", icon="success"),
            create_toast(page, "load-review", "Daily Reflection", icon="info"),
        ],
        fluid=True,
        className="p-0",
    )
