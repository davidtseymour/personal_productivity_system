#Todo: cleaning up placeholder structure to add zeros to hours/minutes when the other is filled and the other two colums are not filled
#Todo
# - Logic for the track goals graphs??

from dash import Input, Output, ctx, State
from src.logic.pages.patterns_trends import plot_cat_from_store


def register_trends_callbacks(app):
    @app.callback(
        Output("productivity-graph", "figure"),
        [
            Input("btn-inf", "n_clicks"),
            Input("btn-30", "n_clicks"),
            Input("btn-14", "n_clicks"),
            Input("btn-7", "n_clicks"),
            Input("btn-1", "n_clicks"),
            Input("category-dropdown", "value"),
            State("date-range-store", "data"),
            State("task-summary-store", "data"),
            State("trends-category-dict-store", "data"),
        ]
    )
    def update_productivity_graph(n_inf, n_30, n_14, n_7, n_1, category_id, date_value, task_summary_store, category_dict):


        # Default day range (if nothing triggered)
        default_days = 1
        button_to_days = {
            "btn-1": 1,
            "btn-7": 7,
            "btn-14": 14,
            "btn-30": 30,
            "btn-inf": -1,
        }

        triggered_id = ctx.triggered_id  # None on initial call

        if triggered_id in (None, "category-dropdown"):
            num_days = button_to_days.get(date_value, default_days)
        else:
            num_days = button_to_days.get(triggered_id, default_days)

        return plot_cat_from_store(
            task_summary_store, category_dict, str(num_days), category_id=category_id if category_id != "all" else None
        )

    @app.callback(
        Output("date-range-store", "data"),
        Input("btn-1", "n_clicks"),
        Input("btn-7", "n_clicks"),
        Input("btn-14", "n_clicks"),
        Input("btn-30", "n_clicks"),
        Input("btn-inf", "n_clicks"),
        prevent_initial_call=True
    )
    def update_range(n1, n7, n14, n30, ninf):
        return ctx.triggered_id

    @app.callback(
        [
            Output("btn-1", "outline"),
            Output("btn-7", "outline"),
            Output("btn-14", "outline"),
            Output("btn-30", "outline"),
            Output("btn-inf", "outline"),
        ],
        Input("date-range-store", "data"),
    )
    def highlight_buttons(active_id):
        return [
            active_id != "btn-1",
            active_id != "btn-7",
            active_id != "btn-14",
            active_id != "btn-30",
            active_id != "btn-inf",
        ]