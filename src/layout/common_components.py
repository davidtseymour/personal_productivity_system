from dash import html
import dash_bootstrap_components as dbc

def create_toast(
    page: str,
    name: str,
    header: str,
    icon: str = "info",
    duration: int = 4000,
    *,
    right_offset: int = 340,
    top: int = 10,
    width: int = 300,
    z_index: int = 2000,
) -> dbc.Toast:
    """Standardized toast component fixed near the upper-right corner."""
    return dbc.Toast(
        "",  # body is set via callback (children)
        id={"page": page, "type": "toast", "name": name},
        header=header,
        icon=icon,
        duration=duration,
        is_open=False,
        style={
            "position": "fixed",
            "top": top,
            "right": right_offset,
            "width": width,
            "zIndex": z_index,
        },
    )

def labeled_control_row(
    label_text: str,
    control_component,
    *,
    col_width=4,
    label_px: int = 110,
    gap: str = "0.5rem",
    className: str = "mb-3",
):
    """
    One-line label + control, pixel-precise label width, Bootstrap col width preserved.

    Parameters
    ----------
    label_text : str
        Label text.
    control_component : Component
        Any Dash component (dcc.Dropdown, dbc.Input, etc.).
    col_width : int | str
        Bootstrap column width (e.g., 4) or "auto".
    label_px : int
        Fixed pixel width for label area.
    gap : str
        CSS gap between label and control.
    className : str
        Wrapper classes (usually margin bottom).
    """
    return dbc.Col(
        html.Div(
            [
                dbc.Label(
                    label_text,
                    className="mb-0",
                    style={"width": f"{label_px}px", "flexShrink": 0},
                ),
                html.Div(
                    control_component,
                    # minWidth=0 prevents flex overflow issues in narrow columns
                    style={"flexGrow": 1, "minWidth": 0},
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
