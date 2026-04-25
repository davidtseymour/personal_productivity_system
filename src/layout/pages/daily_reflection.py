from datetime import date

from dash import html
import dash_bootstrap_components as dbc

from src.layout.common_components import create_toast


def create_daily_reflection() -> dbc.Container:
    page = "daily-reflection"

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Reflection"))),

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
                            dbc.Label("Intentionality score (1–10)"),
                            dbc.Input(
                                id={"page": page, "name": "intentionality-score", "type": "input"},
                                type="number",
                                min=1,
                                max=10,
                                style={"width": "5rem"},
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
