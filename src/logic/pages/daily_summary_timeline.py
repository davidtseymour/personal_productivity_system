import heapq
from datetime import date
from typing import Any

from src.helpers.general import fmt_h_m
from src.layout.common_components import empty_fig
from src.logic.pages.category_colors import ordered_category_color_map
import pandas as pd
import plotly.graph_objects as go

_ACTIVE_SPAN_PADDING_MINUTES = 30
_WORKDAY_START_HOUR = 6
_WORKDAY_END_HOUR = 22
_TIMELINE_TINT = 0.18
_INTERVAL_COLUMNS = [
    "task_id",
    "category_id",
    "category",
    "subcategory",
    "activity",
    "start_at",
    "end_at",
    "display_start",
    "display_end",
    "display_duration_min",
    "clipped_left",
    "clipped_right",
]


def _empty_interval_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_INTERVAL_COLUMNS)


def _get_day_window(summary_date: str | date) -> tuple[pd.Timestamp, pd.Timestamp]:
    day_start = pd.to_datetime(summary_date, errors="coerce")
    if pd.isna(day_start):
        day_start = pd.Timestamp.today().normalize()
    else:
        day_start = day_start.normalize()
    day_end = day_start + pd.Timedelta(days=1)
    return day_start, day_end


def _format_time_label(value: pd.Timestamp) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _format_clip_note(clipped_left: bool, clipped_right: bool) -> str:
    if clipped_left and clipped_right:
        return "Continues outside selected day"
    if clipped_left:
        return "Started before selected day"
    if clipped_right:
        return "Ends after selected day"
    return ""


def normalize_intervals(task_rows: pd.DataFrame | None, summary_date: str | date) -> pd.DataFrame:
    """
    Normalize task rows into clipped intervals that intersect the selected day.
    """
    if task_rows is None or task_rows.empty:
        return _empty_interval_df()

    day_start, day_end = _get_day_window(summary_date)
    df = task_rows.copy()

    required_columns = {"task_id", "category", "subcategory", "activity", "start_at", "end_at"}
    if not required_columns.issubset(df.columns):
        return _empty_interval_df()

    df["start_at"] = pd.to_datetime(df["start_at"], errors="coerce")
    df["end_at"] = pd.to_datetime(df["end_at"], errors="coerce")
    df = df.dropna(subset=["start_at", "end_at"])
    df = df[df["end_at"] > df["start_at"]].copy()
    if df.empty:
        return _empty_interval_df()

    intersects_selected_day = (df["start_at"] < day_end) & (df["end_at"] > day_start)
    df = df[intersects_selected_day].copy()
    if df.empty:
        return _empty_interval_df()

    df["display_start"] = df["start_at"].clip(lower=day_start, upper=day_end)
    df["display_end"] = df["end_at"].clip(lower=day_start, upper=day_end)
    df = df[df["display_end"] > df["display_start"]].copy()
    if df.empty:
        return _empty_interval_df()

    df["task_id"] = pd.to_numeric(df["task_id"], errors="coerce")
    df = df.dropna(subset=["task_id"])
    if df.empty:
        return _empty_interval_df()

    if "category_id" not in df.columns:
        df["category_id"] = pd.NA

    df["task_id"] = df["task_id"].astype(int)
    df["category_id"] = pd.to_numeric(df["category_id"], errors="coerce").astype("Int64")
    df["category"] = df["category"].fillna("Uncategorized").astype(str)
    df["subcategory"] = df["subcategory"].fillna("").astype(str)
    df["activity"] = df["activity"].fillna("").astype(str)
    df["display_duration_min"] = (df["display_end"] - df["display_start"]).dt.total_seconds() / 60
    df["clipped_left"] = df["start_at"] < day_start
    df["clipped_right"] = df["end_at"] > day_end

    return (
        df[_INTERVAL_COLUMNS]
        .sort_values(["display_start", "display_end", "task_id"])
        .reset_index(drop=True)
    )


def assign_tracks(intervals: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Assign non-overlapping track indices using a min-heap sweep (O(n log n)).
    """
    if intervals.empty:
        out = intervals.copy()
        out["track"] = pd.Series(dtype=int)
        out["track_label"] = pd.Series(dtype=str)
        return out, 0

    ordered = intervals.reset_index(drop=True).copy()
    sweep = [
        (pd.Timestamp(row["display_start"]), pd.Timestamp(row["display_end"]), int(idx))
        for idx, row in ordered.iterrows()
    ]
    sweep.sort(key=lambda item: (item[0], item[1], item[2]))

    active_tracks: list[tuple[pd.Timestamp, int]] = []
    free_tracks: list[int] = []
    track_by_idx: dict[int, int] = {}
    next_track = 0

    for start_at, end_at, idx in sweep:
        while active_tracks and active_tracks[0][0] <= start_at:
            _, released = heapq.heappop(active_tracks)
            heapq.heappush(free_tracks, released)

        if free_tracks:
            track = heapq.heappop(free_tracks)
        else:
            track = next_track
            next_track += 1

        track_by_idx[idx] = track
        heapq.heappush(active_tracks, (end_at, track))

    ordered["track"] = [track_by_idx[i] for i in range(len(ordered))]
    ordered["track_label"] = ordered["track"].map(lambda track_num: f"Lane {track_num + 1}")
    return ordered, next_track


def compute_horizon_window(
    intervals: pd.DataFrame,
    summary_date: str | date,
) -> dict[str, Any]:
    """
    Compute axis window and tick spacing for timeline rendering.
    """
    day_start, day_end = _get_day_window(summary_date)
    workday_start = day_start + pd.Timedelta(hours=_WORKDAY_START_HOUR)
    workday_end = day_start + pd.Timedelta(hours=_WORKDAY_END_HOUR)

    if intervals.empty:
        active_start = workday_start
        active_end = workday_end
    else:
        pad = pd.Timedelta(minutes=_ACTIVE_SPAN_PADDING_MINUTES)
        active_start = intervals["display_start"].min() - pad
        active_end = intervals["display_end"].max() + pad
        active_start = max(active_start, day_start)
        active_end = min(active_end, day_end)

    axis_start = min(workday_start, active_start)
    axis_end = max(workday_end, active_end)
    axis_start = max(axis_start, day_start)
    axis_end = min(axis_end, day_end)

    if axis_end <= axis_start:
        axis_end = axis_start + pd.Timedelta(hours=1)

    span_minutes = (axis_end - axis_start).total_seconds() / 60
    if span_minutes <= 6 * 60:
        tick_minutes = 30
    elif span_minutes <= 12 * 60:
        tick_minutes = 60
    elif span_minutes <= 18 * 60:
        tick_minutes = 120
    else:
        tick_minutes = 180

    return {
        "start_at": axis_start,
        "end_at": axis_end,
        "mode": "workday-or-active",
        "tick_minutes": tick_minutes,
    }


def _build_timeline_category_color_map(
    tracked: pd.DataFrame,
    category_order: list[str] | None = None,
) -> dict[str, str]:
    present_categories = [
        str(value).strip()
        for value in tracked["category"].dropna().unique().tolist()
        if str(value).strip()
    ]
    if not present_categories:
        return {}

    if category_order:
        canonical_order = [str(value).strip() for value in category_order if str(value).strip()]
        for category in sorted(present_categories, key=lambda value: value.lower()):
            if category not in canonical_order:
                canonical_order.append(category)
    else:
        canonical = tracked[["category_id", "category"]].copy()
        canonical["category"] = canonical["category"].astype(str).str.strip()
        canonical = canonical[canonical["category"] != ""]

        canonical["has_id"] = canonical["category_id"].notna()
        canonical["category_id_num"] = pd.to_numeric(canonical["category_id"], errors="coerce")
        canonical["sort_id"] = canonical["category_id_num"].fillna(10**9).astype(int)

        canonical = canonical.sort_values(
            ["has_id", "sort_id", "category"],
            ascending=[False, True, True],
        )
        canonical_order = canonical["category"].drop_duplicates().tolist()

    full_color_map = ordered_category_color_map(canonical_order, tint=_TIMELINE_TINT)
    return {
        category: full_color_map.get(category, "#7588FA")
        for category in present_categories
    }


def build_timeline_figure(
    task_rows: pd.DataFrame | None,
    summary_date: str | date,
    category_order: list[str] | None = None,
) -> go.Figure:
    if task_rows is None or task_rows.empty:
        return empty_fig("No timestamped tasks logged for this day.")

    intervals = normalize_intervals(task_rows, summary_date)
    if intervals.empty:
        return empty_fig("No task intervals overlap the selected day.")

    tracked, track_count = assign_tracks(intervals)
    horizon = compute_horizon_window(tracked, summary_date)
    categories = sorted(tracked["category"].unique(), key=lambda value: value.lower())
    color_map = _build_timeline_category_color_map(tracked, category_order=category_order)

    fig = go.Figure()
    for category in categories:
        cat_rows = tracked[tracked["category"] == category].copy()
        if cat_rows.empty:
            continue

        durations_ms = (cat_rows["display_end"] - cat_rows["display_start"]).dt.total_seconds() * 1000
        custom_data = []
        for _, row in cat_rows.iterrows():
            subcategory = row["subcategory"] if row["subcategory"] else "None"
            activity = row["activity"] if row["activity"] else "None"
            start_label = _format_time_label(pd.Timestamp(row["display_start"]))
            end_label = _format_time_label(pd.Timestamp(row["display_end"]))
            clip_note = _format_clip_note(bool(row["clipped_left"]), bool(row["clipped_right"]))
            clip_note_display = f"<br>{clip_note}" if clip_note else ""
            custom_data.append(
                [
                    f"{category} / {subcategory}",
                    activity,
                    start_label,
                    end_label,
                    fmt_h_m(float(row["display_duration_min"])),
                    clip_note_display,
                ]
            )

        fig.add_trace(
            go.Bar(
                orientation="h",
                y=cat_rows["track_label"],
                x=durations_ms,
                base=cat_rows["display_start"],
                name=category,
                legendgroup=category,
                marker=dict(
                    color=color_map.get(category, "#4E79A7"),
                    line=dict(color="#ffffff", width=1),
                ),
                customdata=custom_data,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Start: %{customdata[2]}<br>"
                    "End: %{customdata[3]}<br>"
                    "Duration: %{customdata[4]}"
                    "%{customdata[5]}<extra></extra>"
                ),
                width=0.82,
            )
        )

    lane_labels = [f"Lane {idx + 1}" for idx in range(track_count)]
    timeline_height = min(312, max(132, 74 + (track_count * 20)))

    fig.update_layout(
        barmode="overlay",
        margin=dict(l=0, r=0, t=0, b=42),
        template="plotly_white",
        plot_bgcolor="#f8f9fa",
        hovermode="closest",
        dragmode=False,
        height=timeline_height,
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

    fig.update_yaxes(
        title_text="",
        categoryorder="array",
        categoryarray=list(reversed(lane_labels)),
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#dee2e6",
        linewidth=1,
        mirror=True,
        showticklabels=False,
        tickfont=dict(size=11, color="#495057"),
    )
    fig.update_xaxes(
        title_text="Time",
        type="date",
        range=[horizon["start_at"], horizon["end_at"]],
        dtick=int(horizon["tick_minutes"]) * 60 * 1000,
        tickformat="%-I %p",
        showline=True,
        linecolor="#dee2e6",
        linewidth=1,
        mirror=True,
        zeroline=False,
        gridcolor="#e9ecef",
        gridwidth=1,
    )

    return fig
