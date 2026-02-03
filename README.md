# Productivity System — time logging + daily metrics (Dash)

A personal productivity system built in Dash for logging time, tracking daily metrics, and reviewing summaries/trends.

## What this is
This project is a lightweight Dash app that supports:
- **Time logging** (tasks with category / subcategory / activity / notes)
- **Daily metrics** (entered as numeric values; some can be converted to minutes for time accounting)
- **Daily / weekly summaries** and basic trend views

It’s designed around a simple idea: keep the UI fast, keep the data model explicit, and make it easy to extend.

## Current status
- Core app and UI are in place.
- The repository is intentionally **sanitized** (no personal data, no credentials).
- Database initialization / bootstrap scripts may be excluded or incomplete in the public version.

## Tech stack
- Python
- Dash (+ dash-bootstrap-components)
- pandas / numpy / scipy
- SQLAlchemy + psycopg2
- python-dotenv

## Repo structure (high level)
- `app.py` — Dash app entry point
- `src/`
  - `callbacks/` — Dash callbacks
  - `layout/` — UI layout components and pages
  - `logic/` — page/business logic
  - `helpers/` — validation + adapters
  - `data_access/` — database access layer

## Running locally
This repo assumes a local Python environment and a Postgres database.

### 1) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Set environment variables
Create a `.env` file (not committed) with:
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`

### 4) Run the app
```bash
python app.py
```

## Notes
- `.env` and local data artifacts are ignored via `.gitignore`.
- This is a personal productivity project; the UI and schema are evolving.
