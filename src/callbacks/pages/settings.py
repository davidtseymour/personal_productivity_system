from dash import Input, Output, ctx
from dash.exceptions import PreventUpdate


def register_settings_callbacks(app):
    @app.callback(
        Output("edit-setting-modal", "is_open"),
        Input({"page": "settings", "name": "edit-categories", "type": "button"}, "n_clicks"),
        Input({"page": "settings", "name": "edit-metrics", "type": "button"}, "n_clicks"),
        Input({"page": "settings-modal", "name": "cancel", "type": "button"}, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_settings_modal(n_edit_categories, n_edit_metrics, n_cancel):
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        name = triggered_id.get("name")
        if name in {"edit-categories", "edit-metrics"}:
            return True
        if name == "cancel":
            return False

        raise PreventUpdate
