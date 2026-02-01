import pandas as pd
from dash import html
import dash_bootstrap_components as dbc

def df_to_weekly_html_table(
    df: pd.DataFrame,
    daily_metrics: pd.DataFrame,
    fmt_minutes_fn,          # e.g. fmt_h_m (minutes -> "1h 26m")
    fmt_metric_fn,           # e.g. fmt_int_display or lambda x: f"{to_int(x):,}"
    title: str | None = None,
    show_row_averages: bool = True,     # last column is "Average" (per row)
    show_bottom_totals: bool = True,    # bottom row is "Total" per day (sum across rows)
    highlight_rows: dict[str, dict] | None = None,  # e.g. {"Screen": {"color":"#b00020","fontWeight":"600"}}
    excluded_rows: list[str] | None = None,         # e.g. ["Screen", "Sleep"]
):
    """
    df: pivoted minutes df (index=category/metric, columns=dates, values=minutes)
    daily_metrics: pivoted metrics df (index=metric_key, columns=dates, values=numeric), same date columns ideal
    fmt_minutes_fn: formatter for minutes values in df
    fmt_metric_fn: formatter for non-minute daily_metrics (e.g., steps)
    """
    if df is None or df.empty:
        return html.Small("No data available.", className="text-muted")

    excluded_rows = excluded_rows or ["Screen", "Sleep"]

    # --- Split top/bottom blocks ---
    df_top = df.drop(index=excluded_rows, errors="ignore")

    # Bottom/context rows (safe even if missing)
    df_bottom = df.reindex(excluded_rows).dropna(how="all")

    # Daily metrics block (safe)
    df_metrics = daily_metrics.copy() if daily_metrics is not None else pd.DataFrame()
    if df_metrics is None:
        df_metrics = pd.DataFrame()

    # --- Align columns (dates) across all blocks, preserve df_top column order ---
    date_cols = list(df_top.columns)

    df_top = df_top.reindex(columns=date_cols, fill_value=0)

    if not df_bottom.empty:
        df_bottom = df_bottom.reindex(columns=date_cols, fill_value=0)

    if not df_metrics.empty:
        df_metrics = df_metrics.reindex(columns=date_cols, fill_value=0)

    # --- Column labels (dates) ---
    col_labels = []
    for c in date_cols:
        try:
            col_labels.append(pd.to_datetime(c).strftime("%a %b %d"))
        except Exception:
            col_labels.append(str(c))

    # --- Header (only "Average" bold; everything else normal) ---
    header_cells = [html.Th("", className="fw-normal")]
    header_cells += [html.Th(lbl, className="text-end fw-normal") for lbl in col_labels]
    if show_row_averages:
        header_cells.append(html.Th("Average", className="text-end fw-bold"))
    thead = html.Thead(html.Tr(header_cells))

    # --- Totals/averages (TOP only) ---
    top_row_avgs = df_top.mean(axis=1) if show_row_averages else None

    # Bottom row = TOTAL per day (sum across top rows)
    top_day_totals = df_top.sum(axis=0) if show_bottom_totals else None

    # Bottom-right cell (under "Average" column) = average daily total (mean of day totals)
    # If you'd prefer weekly total instead, use top_day_totals.sum()
    bottom_right = float(top_day_totals.mean()) if (show_bottom_totals and show_row_averages) else None

    # Bottom/context averages (not included in totals)
    bottom_row_avgs = df_bottom.mean(axis=1) if (show_row_averages and not df_bottom.empty) else None

    metrics_row_avgs = df_metrics.mean(axis=1) if (show_row_averages and not df_metrics.empty) else None

    body_rows: list = []

    def _row_style(name: str) -> dict:
        style = {}
        if highlight_rows and name in highlight_rows:
            style.update(highlight_rows[name])
        return style

    # --- TOP rows ---
    for idx, row in df_top.iterrows():
        row_name = str(idx)
        style = _row_style(row_name)

        tds = [html.Td(row_name, style=style)]
        for v in row.values:
            tds.append(html.Td(fmt_minutes_fn(v), className="text-end", style=style))

        if show_row_averages:
            tds.append(html.Td(fmt_minutes_fn(top_row_avgs.loc[idx]), className="text-end fw-bold", style=style))

        body_rows.append(html.Tr(tds))

    # --- Bottom TOTAL row (per day) ---
    if show_bottom_totals:
        total_cells = [html.Td("Total")]
        total_cells += [html.Td(fmt_minutes_fn(v), className="text-end fw-bold") for v in top_day_totals.values]

        if show_row_averages:
            total_cells.append(html.Td(fmt_minutes_fn(bottom_right), className="text-end fw-bold"))

        body_rows.append(
            html.Tr(
                total_cells,
                style={"borderTop": "1px solid #ddd"},
            )
        )

    # --- Spacer + Bottom/context rows (Screen/Sleep) ---
    if not df_bottom.empty:
        # Spacer row (keeps alignment)
        spacer_tds = [html.Td("")]
        spacer_tds += [html.Td("") for _ in date_cols]
        if show_row_averages:
            spacer_tds.append(html.Td(""))
        body_rows.append(html.Tr(spacer_tds, style={"height": "2rem"}))

        for idx, row in df_bottom.iterrows():
            row_name = str(idx)
            style = _row_style(row_name)

            tds = [html.Td(row_name, style=style)]
            for v in row.values:
                tds.append(html.Td(fmt_minutes_fn(v), className="text-end", style=style))

            if show_row_averages:
                tds.append(html.Td(fmt_minutes_fn(bottom_row_avgs.loc[idx]), className="text-end", style=style))

            body_rows.append(html.Tr(tds))

    # --- Spacer + Metrics block (e.g., Steps) ---
    if not df_metrics.empty:
        spacer_tds = [html.Td("")]
        spacer_tds += [html.Td("") for _ in date_cols]
        if show_row_averages:
            spacer_tds.append(html.Td(""))
        body_rows.append(html.Tr(spacer_tds, style={"height": "2rem"}))

        for idx, row in df_metrics.iterrows():
            row_name = str(idx)
            style = _row_style(row_name)

            tds = [html.Td(row_name, style=style)]
            for v in row.values:
                tds.append(html.Td(fmt_metric_fn(v), className="text-end", style=style))

            if show_row_averages:
                tds.append(html.Td(fmt_metric_fn(metrics_row_avgs.loc[idx]), className="text-end", style=style))

            body_rows.append(html.Tr(tds))

    tbody = html.Tbody(body_rows)

    table = dbc.Table(
        [thead, tbody],
        bordered=False,
        hover=True,
        size="sm",
        className="mb-0 weekly-summary-table",
        responsive=True,

    )

    if title:
        return html.Div(
            [
                html.Div(title, className="fw-semibold fs-5 text-center mb-2"),
                table,
            ]
        )

    return table
