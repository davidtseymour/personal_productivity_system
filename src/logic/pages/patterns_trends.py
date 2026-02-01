import pandas as pd
import datetime as dt

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scipy.ndimage import gaussian_filter1d

from src.data_access.db import load_tasks_base_for_view_trend, load_daily_metrics_base_for_view_trend

# -- HELPERS --

BUTTON_TO_DAYS = {
    "btn-1": 1,
    "btn-7": 7,
    "btn-14": 14,
    "btn-30": 30,
    "btn-inf": -1,
}

# -- DATA PROCESSING --

def combine_task_metrics_subcat_agg(user_id: str) -> pd.DataFrame:
    df_tasks = load_tasks_base_for_view_trend(user_id)
    df_metrics = load_daily_metrics_base_for_view_trend(user_id)

    df = pd.concat([df_tasks, df_metrics], ignore_index=True)

    df["date"] = pd.to_datetime(df["date"]).dt.date

    # preserve NULL subcategories
    df = (
        df.groupby(["date", "category_id", "subcategory"], as_index=False, dropna=False)
          .agg(total_minutes=("total_minutes", "sum"))
    )

    return df


def get_task_summary_data(user_id):
    """
    Returns:
      - data_store_return: dict keyed by horizon_days (int) with:
          - horizon_days
          - days_present
          - by_category_hours: {category: hours}
          - by_subcategory_hours: {category: {subcategory: hours}}  (top 8 + Other; subcategory NULL dropped)
      - category_pivot: wide df (date + one column per category, minutes)
    """
    # Base: (date, category, subcategory, total_minutes)
    base_df = combine_task_metrics_subcat_agg(user_id).copy()
    base_df["date"] = pd.to_datetime(base_df["date"]).dt.date

    # Category-level daily totals
    category_df = (
        base_df.groupby(["date", "category_id"], as_index=False)
               .agg(total_minutes=("total_minutes", "sum"))
    )

    today = dt.date.today()
    end = today - dt.timedelta(days=1)  # exclude today

    category_df = category_df[category_df["date"] <= end]

    def _filter_horizon(df, days: int):
        if days > 0:
            start = today - dt.timedelta(days=days)
            return df[(df["date"] >= start) & (df["date"]<=end)].copy()
        return df.copy()

    def _top_n_plus_other(series, n=8, other_label="Other"):
        """
        series: pd.Series indexed by subcategory, values are hours (or minutes)
        returns dict of top n plus 'Other' (sum of remainder)
        """
        if series.empty:
            return {}

        s = series.sort_values(ascending=False)
        top = s.head(n)
        rest = s.iloc[n:]
        out = top.to_dict()
        if not rest.empty:
            out[other_label] = float(rest.sum())
        # ensure plain python floats
        return {k: float(v) for k, v in out.items()}

    data_store_return = {}

    for days in sorted(set(BUTTON_TO_DAYS.values())):
        # ---- category totals (hours) ----
        df_cat = _filter_horizon(category_df, days)
        df_cat["total_hours"] = df_cat["total_minutes"] / 60.0
        days_present = int(df_cat["date"].nunique()) if not df_cat.empty else 0

        by_category_hours = (
            df_cat.groupby("category_id")["total_hours"]
                  .sum()
                  .sort_values(ascending=False)
                  .to_dict()
            if not df_cat.empty else {}
        )
        by_category_hours = {k: float(v) for k, v in by_category_hours.items()}

        # ---- subcategory totals (hours), per category ----
        df_sub = _filter_horizon(base_df, days)
        df_sub = df_sub.dropna(subset=["subcategory"]).copy()
        df_sub["total_hours"] = df_sub["total_minutes"] / 60.0

        by_subcategory_hours = {}
        if not df_sub.empty:
            # sum hours by (category, subcategory)
            sub_sums = (
                df_sub.groupby(["category_id", "subcategory"])["total_hours"]
                      .sum()
            )
            # build per-category dict with top 8 + Other
            for cat in sub_sums.index.get_level_values(0).unique():
                s = sub_sums.loc[cat]
                by_subcategory_hours[cat] = _top_n_plus_other(s, n=8, other_label="Other (grouped)")

        data_store_return[str(days)] = {
            "horizon_days": int(days),
            "days_present": days_present,
            "by_category_hours": by_category_hours,
            "by_subcategory_hours": by_subcategory_hours,
        }

    category_pivot = (
        category_df.pivot_table(
            index="date",
            columns="category_id",
            values="total_minutes",
            fill_value=0,
            aggfunc="sum",
        )
        .reset_index()
    )

    return data_store_return, category_pivot


def plot_ts(ts, category_dict, do_smoothing=True, roll_period=7, smoothing_sigma=1.5):
    """
    Plot a time series with optional rolling average and Gaussian smoothing.

    Args:
        ts (pd.DataFrame): Time series data with dates as the index and one or more columns to plot.
        do_smoothing (bool): Whether to apply Gaussian smoothing after the rolling average.
        roll_period (int): Number of days for the rolling average window.
        smoothing_sigma (float): Sigma parameter for the Gaussian filter.

    Returns:
        fig (plotly.graph_objects.Figure): A Plotly figure containing the smoothed time series plot.

    Notes:
        - Each column in `ts` is plotted as a separate line.
        - Gaussian smoothing is applied using `scipy.ndimage.gaussian_filter1d`.
    """
    # Compute rolling average
    ts = ts[ts["date"] != dt.date.today()]

    ts = ts.set_index('date')
    ts.columns = ts.columns.map(lambda i: category_dict.get(i, i))
    ts = (ts/60).round(1)

    ts_roll = ts.rolling(window=roll_period, min_periods=1).mean()

    # Apply Gaussian smoothing (if enabled)
    if do_smoothing:
        for col in ts_roll.columns:
            ts_roll[col] = gaussian_filter1d(ts_roll[col], sigma=smoothing_sigma)

    # Create Plotly figure
    fig = go.Figure()
    for col in ts_roll.columns:
        fig.add_trace(go.Scatter(
            x=ts_roll.index,
            y=ts_roll[col],
            mode="lines",
            name=col
        ))

    # Customize layout
    fig.update_layout(
        title=None,
        xaxis_title="Date",
        yaxis_title="Average Daily Time (hours)",
        template="plotly_white",
        hovermode="x",
        margin=dict(l=40, r=20, t=40, b=40)
    )

    fig.update_yaxes(rangemode="tozero")

    return fig


def plot_cat_from_store(store_data: dict, category_dict: dict, day_nums: str | int, category_id: str | None = None):
    """
    Plot total time and average weekly time from pre-aggregated datastore JSON.

    This function operates entirely on precomputed aggregates stored in a dcc.Store.
    No filtering, top-N logic, or aggregation is performed here.

    Datastore contract
    ------------------
    store_data is expected to be keyed by `horizon_days`, including `-1` for "all time".

    Each horizon entry must have the form:

        store_data[days] = {
            "horizon_days": int,
            "days_present": int,
            "by_category_hours": {
                <category>: <total_hours>,
                ...
            },
            "by_subcategory_hours": {
                <category>: {
                    <subcategory>: <total_hours>,
                    ...
                },
                ...
            }
        }

    Semantics
    ---------
    - Values are interpreted as *total hours* over the horizon.
    - Average weekly time is computed as:
          total_hours / days_present * 7
    - Ordering is preserved as provided by the datastore.
    - The label "Other (grouped)" is treated as a normal category/subcategory.

    Args:
        store_data (dict):
            Pre-aggregated time summaries from dcc.Store.
        day_nums (int):
            Horizon key (e.g., 1, 7, 28, -1). `-1` denotes "all time".
        category_id (str | None):
            If None, plot category totals.
            If provided, plot subcategory totals within this category.

    Returns:
        plotly.graph_objects.Figure
    """
    horizon = store_data.get(str(day_nums))
    if not horizon:
        return go.Figure().update_layout(
            title="No data available for the selected time window.",
            template="plotly_white"
        )

    days_present = int(horizon.get("days_present", 0) or 0)
    if days_present <= 0:
        return go.Figure().update_layout(
            title="No data available in the selected time window.",
            template="plotly_white"
        )

    if category_id is None:
        totals_raw = horizon.get("by_category_hours") or {}  # {"19": 0.7, "20": 2.8, ...}

        # 2) map to names
        cat_map = {str(k): v for k, v in category_dict.items()}

        totals_name = {cat_map.get(str(cid), None): val for cid, val in totals_raw.items()}
        totals_name = {k: v for k, v in totals_name.items() if k is not None}

        # 3) order by value desc
        totals = dict(sorted(totals_name.items(), key=lambda kv: kv[1], reverse=True))

        title_left = "Total time by category"
        title_right = f"Average time per week by category (over {days_present} days)"
    else:
        totals = (
            horizon
            .get("by_subcategory_hours", {})
            .get(category_id, {})
        ) or {}

        name = category_dict.get(category_id)
        name = name.strip() if isinstance(name, str) else None
        category_suffix = f" ({name})" if name else ""

        title_left = f"Total time by subcategory{category_suffix}"
        title_right = f"Average time per week by subcategory{category_suffix} (over {days_present} days)"

    if not totals:
        return go.Figure().update_layout(
            title="No data available for the selected selection.",
            template="plotly_white"
        )

    x = list(totals.keys())
    y_total = [float(totals[k]) for k in x]
    y_avg = [v / days_present * 7.0 for v in y_total]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[title_left, title_right]
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=y_total,
            text=[round(v, 1) for v in y_total],
            textposition="outside",
            name="Total Time",
            marker_color="skyblue",
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Bar(
            x=x,
            y=y_avg,
            text=[round(v, 2) for v in y_avg],
            textposition="outside",
            name="Average Time",
            marker_color="lightgreen",
        ),
        row=1,
        col=2
    )

    if max(y_total) > 0:
        fig.update_yaxes(range=[0, max(y_total) * 1.1], row=1, col=1)
    if max(y_avg) > 0:
        fig.update_yaxes(range=[0, max(y_avg) * 1.1], row=1, col=2)

    fig.update_layout(
        showlegend=False,
        template="plotly_white",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_tickangle=-45,
        xaxis2_tickangle=-45,
        title_text=None
    )

    fig.update_xaxes(title=None)
    fig.update_yaxes(title_text="Total Time (hours)", row=1, col=1)
    fig.update_yaxes(title_text="Avg Time per Week (hours)", row=1, col=2)

    return fig
