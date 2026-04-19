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
