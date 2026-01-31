from datetime import date

import dash_bootstrap_components as dbc
from dash import html

from src.layout.common_components import create_toast, labeled_control_row


def create_daily_metrics() -> dbc.Form:
    # TODO: Edit layout to get it from database
    # - determine whether layout should be different for different users (probably yes)

    page = "daily-metrics"

    def input_(name: str, placeholder: str, width: str = "140px") -> dbc.Input:
        return dbc.Input(
            id={"page": page, "name": name, "type": "input"},
            type="text",
            placeholder=placeholder,
            style={"width": width, "textAlign": "right"},
            autoComplete="off",
            debounce=True,
        )

    rows = [
        ("Sleep time", input_("sleep_minutes", "150 or 2:30")),
        ("Sleep score", input_("sleep_score", "78")),
        ("Steps", input_("steps", "12000")),
        ("RHR", input_("rhr", "58")),
        ("Stress", input_("stress", "35")),
        ("Phone screen", input_("screen_minutes", "190 or 3:10")),
    ]

    # Label width (140px) + input width (140px) + gap (~8px)
    date_input_width_px = 288

    return dbc.Form(
        [
            html.H5("Daily Metrics"),

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
                                style={"width": f"{date_input_width_px}px"},
                            ),
                        ]
                    )
                ],
                className="mb-4",
            ),

            *[
                labeled_control_row(
                    label,
                    control,
                    col_width=12,
                    label_px=140,
                    className="mb-3",
                )
                for label, control in rows
            ],

            dbc.Button(
                "Save Metrics",
                id={"page": page, "name": "save-metrics", "type": "button"},
                color="primary",
            ),

            create_toast(page, "save-metrics", "Daily Metrics", icon="success"),
        ]
    )
