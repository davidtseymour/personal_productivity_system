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
  - Include the event date (and any other minimal context) in the update signal
  - Refresh analytics pages when an edit/delete affects the active date range
  - Don’t do full refreshes—only update what the current view depends on:
    - analytics figures/tables 
    - sidebar summaries 
    - daily metrics display 
    - any views that include the edited/deleted items

- Bring other todos into this file as valuable

### Specific Pages
**Log Time**
- Logic for having list of frequent subcategories and activities
  - The subcategories suggestions should be based on previous activities
- Implement convert to dictionary as passthrough
  - Improves code generalizability and improvement
- Refactor log time and edit time to make sure they maintain consistency