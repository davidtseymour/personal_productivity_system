from datetime import date

import dash_bootstrap_components as dbc
from dash import html

from src.data_access.db import get_daily_metrics_definitions
from src.layout.common_components import create_toast, labeled_control_row
from src.logic.pages.daily_metric import metric_placeholder, normalize_metric_definitions


def create_daily_metrics(user_id) -> dbc.Form:
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

    metrics_list = get_daily_metrics_definitions(user_id)
    norm_metric_list = normalize_metric_definitions(metrics_list)

    rows = [
        (
            m["display_name"],
            input_(m["metric_key"], metric_placeholder(m["is_duration"])),
        )
        for m in norm_metric_list
    ]

    # Label width (140px) + input width (140px) + gap (~8px)
    date_input_width_px = 288
    if len(rows) == 0:
        return dbc.Form(
            [
                html.H5("Daily Metrics"),
                html.Small("No active metrics.", className="text-muted")
            ])

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
