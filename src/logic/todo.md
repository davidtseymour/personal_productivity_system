### TODO

- Plan backup structure for DB
  - periodic backups (strategy + schedule)
  - table exports (CSV/Parquet) / pg_dump

- Spinning refresh button

- Settings page
  - category display names
  - presets/defaults (e.g., 2-hour warning for entered tasks)

- Improve toasts
  - add toasts for actions that currently don’t have them
  - validation toasts should be specific (new/edit task)

- Strategy for editing tasks once off the sidebar
  - likely via a "task history" page

- Ensure data updates refresh the relevant components
  - every write produces an update event (date/type/time) stored in dcc.Store("last-update") or DB
  - refresh only what the current view needs:
    - analytics figures/tables
    - sidebar summaries
    - daily metrics display
    - views showing edited/deleted items

- Bring other todos into this file as valuable