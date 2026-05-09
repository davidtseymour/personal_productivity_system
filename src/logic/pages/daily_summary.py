import heapq
from datetime import date
from typing import Any, Callable

from dash import html
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.data_access.db import (
    load_category_id_to_name,
    load_metrics_base_for_daily_summary,
    load_task_base_for_daily_summary,
    load_tasks_for_day,
)
from src.helpers.general import fmt_h_m
from src.layout.common_components import empty_fig


def df_to_daily_html_table(
    df: pd.DataFrame | None,
    fmt_minutes_fn: Callable[[float], str],
    highlight_rows: dict[Any, dict[str, Any]] | None = None,
) -> dbc.Table | None:
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

    def _row_style(cat: str, sub: str) -> dict[str, Any]:
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


def get_subcategory_df_for_date(user_id: str, summary_date: str | date) -> pd.DataFrame:
    task_summary = load_task_base_for_daily_summary(user_id, summary_date=summary_date)
    daily_summary = load_metrics_base_for_daily_summary(user_id, summary_date=summary_date)

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


def get_today_subcategory_df(user_id: str) -> pd.DataFrame:
    return get_subcategory_df_for_date(user_id, date.today())


def get_task_timeline_df_for_date(user_id: str, summary_date: str | date) -> pd.DataFrame:
    task_rows = load_tasks_for_day(user_id, selected_date=summary_date)
    if task_rows is None or task_rows.empty:
        return pd.DataFrame()

    df = task_rows.copy()
    df["start_at"] = pd.to_datetime(df["start_at"], errors="coerce")
    df["end_at"] = pd.to_datetime(df["end_at"], errors="coerce")
    df = df.dropna(subset=["start_at", "end_at"])
    df = df[df["end_at"] > df["start_at"]].copy()

    if df.empty:
        return pd.DataFrame()

    df["category"] = df["category"].fillna("Uncategorized")
    df["subcategory"] = df["subcategory"].fillna("")
    df["activity"] = df["activity"].fillna("")
    df["duration_min"] = df["duration_min"].fillna(0).astype(int)

    return df.sort_values(["start_at", "task_id"]).reset_index(drop=True)

def _assign_overlap_tracks(task_rows: pd.DataFrame) -> tuple[list[int], int]:
    intervals: list[tuple[pd.Timestamp, pd.Timestamp, int]] = []
    for idx, row in task_rows.iterrows():
        intervals.append(
            (
                pd.Timestamp(row["start_at"]),
                pd.Timestamp(row["end_at"]),
                int(idx),
            )
        )

    intervals.sort(key=lambda x: (x[0], x[1], x[2]))

    active: list[tuple[pd.Timestamp, int]] = []
    free_tracks: list[int] = []
    track_by_idx: dict[int, int] = {}
    next_track = 0

    for start_at, end_at, idx in intervals:
        while active and active[0][0] <= start_at:
            _, freed_track = heapq.heappop(active)
            heapq.heappush(free_tracks, freed_track)

        if free_tracks:
            track = heapq.heappop(free_tracks)
        else:
            track = next_track
            next_track += 1

        track_by_idx[idx] = track
        heapq.heappush(active, (end_at, track))

    tracks = [track_by_idx[i] for i in range(len(task_rows))]
    return tracks, next_track


def _overlap_count_per_task(task_rows: pd.DataFrame) -> list[int]:
    if task_rows.empty:
        return []

    starts = [pd.Timestamp(v) for v in task_rows["start_at"].tolist()]
    ends = [pd.Timestamp(v) for v in task_rows["end_at"].tolist()]
    overlap_counts: list[int] = []

    for idx, (start_at, end_at) in enumerate(zip(starts, ends)):
        overlap_count = 0
        for other_idx, (other_start, other_end) in enumerate(zip(starts, ends)):
            if idx == other_idx:
                continue
            if other_start < end_at and other_end > start_at:
                overlap_count += 1
        overlap_counts.append(overlap_count)

    return overlap_counts


def make_task_timeline_fig(
    task_rows: pd.DataFrame | None,
    summary_date: str | date,
) -> go.Figure:
    if task_rows is None or task_rows.empty:
        return empty_fig("No timestamped tasks logged for this day.")

    day_start = pd.to_datetime(summary_date).normalize()

    df = task_rows.copy().reset_index(drop=True)
    tracks, track_count = _assign_overlap_tracks(df)
    df["track"] = tracks
    df["overlap_count"] = _overlap_count_per_task(df)
    lane_names = {i: f"_lane_{i}" for i in range(track_count)}
    timeline_line_width = 70

    default_axis_start = day_start + pd.Timedelta(hours=6)
    default_axis_end = day_start + pd.Timedelta(hours=22)
    earliest_task_start = pd.Timestamp(df["start_at"].min()).floor("h")
    latest_task_end = pd.Timestamp(df["end_at"].max()).ceil("h")
    axis_start = min(default_axis_start, earliest_task_start)
    axis_end = max(default_axis_end, latest_task_end)
    if axis_end <= axis_start:
        axis_end = axis_start + pd.Timedelta(hours=1)

    palette = [
        "#4E79A7",
        "#59A14F",
        "#E15759",
        "#F28E2B",
        "#76B7B2",
        "#EDC948",
        "#B07AA1",
        "#9C755F",
        "#FF9DA7",
    ]
    categories = df["category"].drop_duplicates().tolist()
    color_map = {name: palette[i % len(palette)] for i, name in enumerate(categories)}

    fig = go.Figure()
    legend_seen: set[str] = set()

    for _, row in df.iterrows():
        category = str(row["category"])
        lane = lane_names.get(int(row["track"]), "Tasks")
        start_at = pd.to_datetime(row["start_at"])
        end_at = pd.to_datetime(row["end_at"])
        overlap_count = max(int(row.get("overlap_count", 0)), 0)

        shrink_fraction = 1.0 / (3.0 + float(overlap_count))
        duration = end_at - start_at
        shrink_delta = duration * shrink_fraction
        draw_start = start_at + (shrink_delta / 2)
        draw_end = end_at - (shrink_delta / 2)
        if draw_end <= draw_start:
            draw_start = start_at
            draw_end = end_at

        showlegend = category not in legend_seen
        legend_seen.add(category)

        fig.add_trace(
            go.Scatter(
                x=[draw_start, draw_end],
                y=[lane, lane],
                mode="lines",
                name=category,
                legendgroup=category,
                showlegend=showlegend,
                hoverinfo="skip",
                line=dict(
                    color=color_map.get(category, "#4E79A7"),
                    width=timeline_line_width,
                ),
            )
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=34),
        template="plotly_white",
        plot_bgcolor="#f8f9fa",
        hovermode=False,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.20,
            xanchor="left",
            x=0.0,
            title_text="",
        ),
    )

    lane_order = [lane_names[i] for i in range(track_count - 1, -1, -1)]
    lane_min = -0.5
    lane_max = track_count - 0.5
    fig.update_yaxes(
        title_text="",
        categoryorder="array",
        categoryarray=lane_order,
        range=[lane_min, lane_max],
        showticklabels=False,
        ticks="",
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#dee2e6",
        linewidth=1,
        mirror=True,
        ticklabelstandoff=3,
    )
    fig.update_xaxes(
        title_text="Time",
        range=[axis_start, axis_end],
        dtick=2 * 60 * 60 * 1000,
        tickformat="%-I %p",
        showline=True,
        linecolor="#dee2e6",
        linewidth=1,
        mirror=True,
        zeroline=False,
    )

    return fig


def make_stacked_subcategory_fig(df: pd.DataFrame | None) -> go.Figure:
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
    fill_color = "skyblue"
    sep_color = "#ffffff"


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
                    line=dict(color=sep_color, width=1),
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
