from typing import Any

from dash import html
import dash_bootstrap_components as dbc


def _date_input(input_id: dict[str, str], selected_date: str) -> dbc.Input:
    return dbc.Input(
        id=input_id,
        type="date",
        value=selected_date,
        style={
            "width": "calc(100% + 1.125rem)",
            "marginLeft": "-1.125rem",
        },
    )


def _date_cycler_buttons(
    page: str,
    *,
    prev_name: str,
    next_name: str,
    prev_tooltip: str,
    next_tooltip: str,
) -> dbc.Col:
    return dbc.Col(
        [
            dbc.Button(
                html.I(className="bi bi-chevron-left", style={"fontSize": "1.2rem"}),
                id={"page": page, "name": prev_name, "type": "button"},
                color="light",
                size="sm",
                className="rounded-circle me-2",
                style={
                    "width": "32px",
                    "height": "32px",
                    "padding": "0",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
                n_clicks=0,
            ),
            dbc.Button(
                html.I(className="bi bi-chevron-right", style={"fontSize": "1.2rem"}),
                id={"page": page, "name": next_name, "type": "button"},
                color="light",
                size="sm",
                className="rounded-circle",
                style={
                    "width": "32px",
                    "height": "32px",
                    "padding": "0",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
                n_clicks=0,
            ),
            dbc.Tooltip(
                prev_tooltip,
                target={"page": page, "name": prev_name, "type": "button"},
                placement="top",
            ),
            dbc.Tooltip(
                next_tooltip,
                target={"page": page, "name": next_name, "type": "button"},
                placement="top",
            ),
        ],
        width="auto",
        className="d-flex align-items-center",
    )


def labeled_fixed_width_control_row(
    label_text: str,
    control_component: Any,
    *,
    control_width: str = "12rem",
    col_width: int | str = "auto",
    label_width: str = "7rem",
    gap: str = "0.5rem",
    className: str = "mb-3",
) -> dbc.Col:
    """One-line label + control with a fixed-width control area."""
    return dbc.Col(
        html.Div(
            [
                dbc.Label(
                    label_text,
                    className="mb-0",
                    style={"width": label_width, "flexShrink": 0},
                ),
                html.Div(
                    control_component,
                    style={"width": control_width, "flexShrink": 0},
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": gap,
                "whiteSpace": "nowrap",
            },
            className=className,
        ),
        width=col_width,
    )


def date_controlled_row(
    page: str,
    selected_date: str,
    className: str = "mb-3",
    *,
    date_name: str = "date",
    label_text: str = "Date",
) -> dbc.Col:
    return (
        labeled_fixed_width_control_row(
            label_text,
            _date_input({"page": page, "name": date_name, "type": "date-input"}, selected_date),
            control_width="8.75rem",
            label_width="8.75rem",
            className=className,
        )
    )


def date_cycler_row(
    page: str,
    selected_date: str,
    *,
    date_name: str = "date",
    label_text: str = "Date",
    prev_name: str,
    next_name: str,
    prev_tooltip: str,
    next_tooltip: str,
    row_class: str = "g-2 align-items-center mb-4",
) -> dbc.Row:
    return dbc.Row(
        [
            date_controlled_row(
                page,
                selected_date,
                className="mb-0",
                date_name=date_name,
                label_text=label_text,
            ),
            _date_cycler_buttons(
                page,
                prev_name=prev_name,
                next_name=next_name,
                prev_tooltip=prev_tooltip,
                next_tooltip=next_tooltip,
            ),
        ],
        className=row_class,
    )
