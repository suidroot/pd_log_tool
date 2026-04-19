# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django 5.1 web application for storing and querying police log records (dispatch calls and arrests). The project root is `/Log-DB-Tool/` with the Django project living in `webproject/`.

## Environment Setup

The app requires a `SECRET_KEY` environment variable. For local development, source the env file before running:

```bash
source /Users/locutus/.virtualenvs/log-db-tool/bin/activate
cd webproject
source load_env.sh   # sources ../dev.env
```

`dev.env` lives one level up from `webproject/` (at the repo root). See `example.env` for required variables.

## Development Commands

All `manage.py` commands run from `webproject/`:

```bash
python manage.py runserver          # Start dev server (SQLite)
python manage.py migrate            # Apply migrations
python manage.py makemigrations     # Create new migrations
python manage.py test               # Run tests
python manage.py test log_query_site  # Run tests for the app
python manage.py createsuperuser    # Create admin user
python manage.py create_api_key --name "csv_loader"  # Generate a CSV loader API key
```

## Production / Docker

Production uses Docker Compose with PostgreSQL. Run from repo root:

```bash
docker-compose up --build
```

Production config is in `webproject/log_site/production.py`. It reads DB credentials (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) and `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` from environment. The `stack.env` file supplies these at runtime.

- Dev: SQLite (`db.sqlite3`), settings in `log_site/settings.py`
- Prod: PostgreSQL via Docker, settings in `log_site/production.py`

## Architecture

```
webproject/
  log_site/          # Django project package (settings, urls, wsgi)
    settings.py      # Dev settings (SQLite)
    production.py    # Production settings (PostgreSQL)
    urls.py          # Root URL config
  log_query_site/    # Main Django app
    models.py        # All data models + record creation logic
    views.py         # All views (search, add, about)
    auth.py          # require_api_key decorator for ingest endpoints
    admin.py         # Admin registrations
    templates/       # HTML templates
    migrations/      # Database migrations
    management/commands/create_api_key.py  # API key generation command

csv_loader/
  loader.py          # CLI tool to POST CSV data to the Django API
```

### Data Model

`PoliceLog` is the central model, referencing lookup tables:
- **Dispatch records**: linked to `DispatchType`, `Disposition`, `Officer`
- **Arrest records**: linked to `Arrestee`, `ArrestType`, `Charge` (M2M), `Officer`
- Both record types use `Municipality` and `RecordType` FKs

Lookup models (`Charge`, `ArrestType`, `DispatchType`, `Disposition`, `Officer`) all implement a `get_or_create` / `search_by_name` / `create` class method pattern to deduplicate entries before saving.

`APIKey` stores hashed API keys (SHA-256) for CSV loader authentication. Only the prefix (first 8 chars) and hash are stored — the raw key is shown once at creation time.

### API Endpoints

Two `@csrf_exempt` POST endpoints accept JSON to ingest records, authenticated via `@require_api_key`:
- `POST /add/arrest/` — expects arrest log fields
- `POST /add/dispatch/` — expects dispatch log fields

The `csv_loader/loader.py` script reads CSV files and POSTs to these endpoints. Configure via environment variables:
- `LOG_DB_API_KEY` — API key (required)
- `LOG_DB_DISPATCH_URL` — defaults to `http://localhost:8000/add/dispatch/`
- `LOG_DB_ARREST_URL` — defaults to `http://localhost:8000/add/arrest/`

### Search

`GET/POST /search` renders the search form with all filter options.
`POST /results` executes the query against `PoliceLog` with optional filters (date range, officer, charge, arrest type, address, record type). Results are capped at `MAX_RESULTS = 100` by default.

## CSV Loader Usage

```bash
export LOG_DB_API_KEY=<key from create_api_key command>
python csv_loader/loader.py -f <file.csv> -m    # load dispatch CSV
python csv_loader/loader.py -f <file.csv> -a    # load arrest CSV
python csv_loader/loader.py -d <directory/> -m  # load directory of CSVs
```

Dispatch CSV columns: `PD Call#`, `Call Start \nDate & Time`, `Call End \nDate & Time`, `Type of Call`, `Street Address / Location`, `Officer Name`

Arrest CSV columns: `Date`, `Arrestee Name`, `Age`, `Home City`, `Charge` (semicolon-separated), `Arrest Type`, `Officer Name`, `Violation Location`
