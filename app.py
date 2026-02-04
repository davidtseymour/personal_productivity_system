from dash import Dash
import dash_bootstrap_components as dbc

from src.layout.layout import create_layout
from src.config.helpers import create_config_dic

from src.callbacks.layout import register_layout_callbacks
from src.callbacks.pages.log_time import register_log_time_callbacks
from src.callbacks.pages.daily_metrics import register_daily_metrics_callbacks
from src.callbacks.pages.goals import register_goals_callbacks
from src.callbacks.pages.daily_reflection import register_daily_reflection_callbacks
from src.callbacks.pages.patterns_trends import register_trends_callbacks
from src.callbacks.overlays import register_overlays_callbacks
from src.callbacks.navigation import register_navigation_callbacks


config = create_config_dic()

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
)

app.title = "Productivity System"
app.layout = create_layout()

# Register callbacks
register_layout_callbacks(app)
register_log_time_callbacks(app)
register_daily_metrics_callbacks(app)
register_daily_reflection_callbacks(app,config)
register_goals_callbacks(app)
register_trends_callbacks(app)
register_overlays_callbacks(app)
register_navigation_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)
