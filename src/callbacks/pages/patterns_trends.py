#Todo: cleaning up placeholder structure to add zeros to hours/minutes when the other is filled and the other two colums are not filled
#Todo
# - Logic for the track goals graphs??
from dash import Dash, Input, Output, State, ctx
from src.logic.pages.patterns_trends import plot_cat_from_store


def register_trends_callbacks(app: Dash) -> None:
    @app.callback(
        Output("productivity-graph", "figure"),
        [
            Input("btn-inf", "n_clicks"),
            Input("btn-365", "n_clicks"),
            Input("btn-28", "n_clicks"),
            Input("btn-14", "n_clicks"),
            Input("btn-7", "n_clicks"),
            Input("btn-1", "n_clicks"),
            Input("category-dropdown", "value"),
            State("date-range-store", "data"),
            State("task-summary-store", "data"),
            State("trends-category-dict-store", "data"),
        ]
    )
    def update_productivity_graph(
        n_inf,
        n_365,
        n_28,
        n_14,
        n_7,
        n_1,
        category_id,
        date_value,
        task_summary_store,
        category_dict,
    ):


        # Default day range (if nothing triggered)
        default_days = 1
        button_to_days = {
            "btn-1": 1,
            "btn-7": 7,
            "btn-14": 14,
            "btn-28": 28,
            "btn-365": 365,
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
        Input("btn-28", "n_clicks"),
        Input("btn-365", "n_clicks"),
        Input("btn-inf", "n_clicks"),
        prevent_initial_call=True
    )
    def update_range(n1, n7, n14, n28, n365, ninf):
        return ctx.triggered_id

    @app.callback(
        [
            Output("btn-1", "outline"),
            Output("btn-7", "outline"),
            Output("btn-14", "outline"),
            Output("btn-28", "outline"),
            Output("btn-365", "outline"),
            Output("btn-inf", "outline"),
        ],
        Input("date-range-store", "data"),
    )
    def highlight_buttons(active_id):
        return [
            active_id != "btn-1",
            active_id != "btn-7",
            active_id != "btn-14",
            active_id != "btn-28",
            active_id != "btn-365",
            active_id != "btn-inf",
        ]
