from dash import html
import dash_bootstrap_components as dbc


def labeled_fixed_width_control_row(
    label_text: str,
    control_component,
    *,
    control_width: str = "12rem",
    col_width="auto",
    label_width: str = "7rem",
    gap: str = "0.5rem",
    className: str = "mb-3",
):
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


def date_controlled_row(page, selected_date, className: str = "mb-3"):
    return (
        labeled_fixed_width_control_row(
            "Date",
            dbc.Input(
                id={"page": page, "name": "date", "type": "date-input"},
                type="date",
                value=selected_date,
            ),
            className=className,
        )
    )


def date_cycler_row(
    page: str,
    selected_date: str,
    *,
    prev_name: str,
    next_name: str,
    prev_tooltip: str,
    next_tooltip: str,
) -> dbc.Row:
    return dbc.Row(
        [
            date_controlled_row(page, selected_date, className="mb-0"),
            dbc.Col(
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
            ),
        ],
        className="g-2 align-items-center mb-2",
    )
