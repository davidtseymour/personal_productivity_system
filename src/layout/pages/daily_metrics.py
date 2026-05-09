from datetime import date

from dash import html
import dash_bootstrap_components as dbc

from src.data_access.db import get_daily_metrics_definitions
from src.layout.common_components import create_toast, labeled_control_row
from src.layout.shared_components.components import date_cycler_row
from src.logic.pages.daily_metric import metric_placeholder, normalize_metric_definitions


def create_daily_metrics_page(user_id: str) -> dbc.Container:
    page = "daily-metrics"
    selected_date = date.today().isoformat()

    def input_(name: str, placeholder: str, width: str = "8.75rem") -> dbc.Input:
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

    if len(rows) == 0:
        body_children = [
            dbc.Row(dbc.Col(html.Small("No active metrics.", className="text-muted"))),
            create_toast(page, "save-metrics", "Daily Metrics", icon="success"),
        ]
    else:
        body_children = [
            *[
                labeled_control_row(
                    label,
                    control,
                    col_width=12,
                    label_width="8.75rem",
                    className="mb-3",
                )
                for label, control in rows
            ],
            dbc.Row(
                dbc.Col(
                    dbc.Button(
                        "Save Metrics",
                        id={"page": page, "name": "save-metrics", "type": "button"},
                        color="primary",
                    ),
                    width=12,
                )
            ),
            create_toast(page, "save-metrics", "Daily Metrics", icon="success"),
        ]

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Metrics")), className="mb-2"),
            date_cycler_row(
                page,
                selected_date,
                prev_name="prev-day",
                next_name="next-day",
                prev_tooltip="Go to previous day",
                next_tooltip="Go to next day",
            ),
            *body_children,
        ],
        fluid=True,
        className="p-0",
    )


def create_daily_metrics(user_id: str) -> dbc.Container:
    return create_daily_metrics_page(user_id)
