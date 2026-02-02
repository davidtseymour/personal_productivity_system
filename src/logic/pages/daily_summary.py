import dash_bootstrap_components as dbc
import numpy as np
from dash import html
import pandas as pd
import plotly.graph_objects as go

from src.data_access.db import load_task_base_for_daily_summary, load_metrics_base_for_daily_summary, \
    load_category_id_to_name
from src.helpers.general import fmt_h_m
from src.layout.common_components import empty_fig


def df_to_daily_html_table(df, fmt_minutes_fn, highlight_rows=None):
    """
    Build a simple daily summary HTML table (Dash + dbc) from a long-form dataframe.

    Expected df columns:
      - category
      - subcategory
      - total_minutes

    Assumptions:
      - df is already cleaned, filtered, aggregated, and sorted upstream.

    Parameters
    ----------
    df
        Pandas DataFrame with columns [category, subcategory, total_minutes].
    fmt_minutes_fn
        Function that formats a minutes value into a display string.
        Example: fmt_h_m(85) -> "1h 25m"
    highlight_rows
        Optional dict mapping a row key to a CSS style dict. You can target:
          1) Category:                {"Screen": {"color":"#b00020","fontWeight":"600"}}
          2) Subcategory:             {"Phone": {"color":"#b00020"}}
          3) (Category, Subcategory): {("Screen","Phone"): {"color":"#b00020","fontWeight":"600"}}

        Specificity precedence:
          (category, subcategory) > category > subcategory

    Returns
    -------
    dbc.Table (Dash component)
    """
    if df is None or df.empty:
        return None # Intentionally blank - "no data" message in right panel

    highlight_rows = highlight_rows or {}

    def _row_style(cat, sub):
        style = {}
        if (cat, sub) in highlight_rows:
            style.update(highlight_rows[(cat, sub)])
        elif cat in highlight_rows:
            style.update(highlight_rows[cat])
        elif sub in highlight_rows:
            style.update(highlight_rows[sub])
        return style

    thead = html.Thead(
        html.Tr(
            [
                html.Th("Category", className="fw-bold"),
                html.Th("Subcategory", className="fw-bold"),
                html.Th("Time", className="text-end fw-bold"),
            ]
        )
    )

    body_rows = []
    for _, r in df.iterrows():
        cat = r["category"]
        sub = r["subcategory"]
        style = _row_style(cat, sub)

        body_rows.append(
            html.Tr(
                [
                    html.Td(cat, style=style),
                    html.Td(sub, style=style),
                    html.Td(fmt_minutes_fn(r["total_minutes"]), className="text-end", style=style),
                ]
            )
        )

    return dbc.Table(
        [thead, html.Tbody(body_rows)],
        bordered=False,
        hover=True,
        size="sm",
        className="mb-0 daily-summary-table",
        responsive=True,
    )


def get_today_subcategory_df(user_id):
    task_summary = load_task_base_for_daily_summary(user_id)
    daily_summary = load_metrics_base_for_daily_summary(user_id)

    # category_dict: {"19": "School", "20": "Activities", ...}
    category_dict = load_category_id_to_name(user_id)
    cat_map = {str(k): v for k, v in category_dict.items()}

    # Normalize types
    for df in (task_summary, daily_summary):
        if df is not None and not df.empty:
            df["category_id"] = df["category_id"].astype("string")

    combined = (
        pd.concat([task_summary, daily_summary], ignore_index=True)
        .groupby(["category_id", "subcategory"], as_index=False)["total_minutes"].sum()
    )

    # Attach names for display
    combined["category"] = combined["category_id"].map(cat_map)

    # Drop sleep by name (or by id if you prefer)
    combined = combined[combined["category"] != "Sleep"]

    combined = (
        combined.sort_values(
            ["total_minutes", "category", "subcategory"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )

    return combined


def make_stacked_subcategory_fig(df):
    """
    Horizontal stacked bar chart:
      - y = category
      - x = total_minutes
      - subcategories stacked within each category
      - all segments same color, separated by thin lines

    Expected columns: category, subcategory, total_minutes
    Assumes df is already cleaned/filtered/aggregated upstream.
    """
    if df is None or df.empty:
        return empty_fig("No productive time logged today.")

    d = df.copy()

    # Category order: largest total on top
    cat_order = (
        d.groupby("category")["total_minutes"].sum()
         .sort_values(ascending=True)  # ascending so largest ends up at top in horizontal bar
         .index.tolist()
    )

    # Build a wide table: rows=category, cols=subcategory
    wide = (
        d.pivot_table(
            index="category",
            columns="subcategory",
            values="total_minutes",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(cat_order)
    )

    subcat_order = wide.sum(axis=0).sort_values(ascending=False).index
    wide = wide[subcat_order]

    fig = go.Figure()

    # Same fill for every subcategory segment
    fill_color = "skyblue"      # bootstrap-ish gray; change if you want
    sep_color = "#ffffff"       # white separators; use "#dee2e6" if your background is not white


    for subcat in wide.columns:
        x = wide[subcat]
        x_fmt = [fmt_h_m(v) for v in x]

        fig.add_trace(
            go.Bar(
                y=wide.index,
                x=x,
                orientation="h",
                name=str(subcat),          # name doesn't matter since we hide legend
                showlegend=False,
                marker=dict(
                    color=fill_color,
                    line=dict(color=sep_color, width=1),  # the separators
                ),
                customdata=x_fmt,
                hovertemplate=(
                    f"{subcat}<br>"
                    "%{customdata}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        barmode="stack",
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_white",
        hoverlabel=dict(
            bordercolor="#adb5bd",  # grey border
            font=dict(color="#212529"),  # dark text (Bootstrap body text)
        )
    )
    fig.update_yaxes(title_text="",
                     ticklabelstandoff=3,)

    max_minutes = float(wide.to_numpy().sum(axis=1).max())
    tick_hours = np.arange(0, max_minutes / 60 + 0.5, 0.5)

    fig.update_xaxes(
        title_text="Hours",
        tickmode="array",
        tickvals=(tick_hours * 60).tolist(),
        ticktext=[f"{h:g}" for h in tick_hours],
    )

    return fig
