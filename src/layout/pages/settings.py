# Todo: Option to edit/add daily metrics
# Todo: Option to edit/add categories.

from dash import html
import dash_bootstrap_components as dbc

def create_settings_page(user_id=None) -> html.Div:
    page = 'settings',

    return (
        dbc.Container(
            [
                html.H5("Settings"),
                html.Label('Edit Categories'),
                html.Br(),
                html.Label('Edit Metrics')
          ],
            fluid=True,
            className="p-0",
        )
    )
