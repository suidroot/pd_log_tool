# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 5.1 web application for storing and searching police log records (dispatch calls and arrests) for Portland Maine PD. The Django project lives in `webproject/`; a standalone CSV ingestion script lives in `csv_loader/`.

## Environment Setup

Requires a `SECRET_KEY` env variable. For local development:

```bash
source /Users/locutus/.virtualenvs/log-db-tool/bin/activate
cd webproject
source load_env.sh   # sources ../dev.env
```

See `example.env` for all required variables. `dev.env` lives at the repo root.

## Development Commands

All `manage.py` commands run from `webproject/`:

```bash
python manage.py runserver              # Start dev server (SQLite, port 8000)
python manage.py migrate                # Apply migrations
python manage.py makemigrations         # Create new migrations
python manage.py test                   # Run all tests
python manage.py test log_query_site    # Run app tests only
python manage.py createsuperuser        # Create admin user
python manage.py create_api_key --name "csv_loader"  # Generate a CSV loader API key
```

## Production / Docker

```bash
docker-compose up --build   # Run from repo root; uses PostgreSQL
```

- Dev: SQLite (`db.sqlite3`), settings in `webproject/log_site/settings.py`
- Prod: PostgreSQL via Docker, settings in `webproject/log_site/production.py`

Production reads `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DJANGO_ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` from `stack.env`.

## Architecture

```
webproject/
  log_site/          # Django project package (settings, urls, wsgi)
    settings.py      # Dev settings (SQLite, DEBUG=True)
    production.py    # Production settings (PostgreSQL)
    urls.py          # Root URL config
  log_query_site/    # Single main Django app
    models.py        # All data models + record creation logic
    views.py         # All views (search, add, about)
    auth.py          # require_api_key decorator for ingest endpoints
    admin.py         # Admin registrations
    templates/       # HTML templates (base.html + per-view)
    management/commands/create_api_key.py  # API key generation command

csv_loader/
  loader.py          # CLI script: reads CSV, POSTs JSON to Django API
```

### Data Model

`PoliceLog` is the central model with two record types (dispatch / arrest), referencing lookup tables:
- **Dispatch**: `DispatchType`, `Disposition`, `Officer`
- **Arrest**: `Arrestee`, `ArrestType`, `Charge` (M2M), `Officer`
- Both: `Municipality`, `RecordType`

All lookup models implement a `get_or_create` / `search_by_name` / `create` class-method pattern to deduplicate entries on ingest.

`APIKey` stores hashed API keys (SHA-256) for CSV loader authentication. Only the key prefix (first 8 chars) and hash are stored — the raw key is shown once at creation and cannot be recovered.

### Key URL Routes

| Route | Purpose |
|-------|---------|
| `GET /` | Home page |
| `GET /about` | Stats / metadata |
| `GET POST /search` | Search form |
| `POST /results` | Execute query (max 100 results) |
| `POST /add/arrest/` | JSON ingest endpoint (`@csrf_exempt`, `@require_api_key`) |
| `POST /add/dispatch/` | JSON ingest endpoint (`@csrf_exempt`, `@require_api_key`) |

### CSV Loader

```bash
export LOG_DB_API_KEY=<key from create_api_key command>
python csv_loader/loader.py -f <file.csv> -m    # load dispatch CSV
python csv_loader/loader.py -f <file.csv> -a    # load arrest CSV
python csv_loader/loader.py -d <directory/> -m  # load directory of CSVs
```

Environment variables for the loader:
- `LOG_DB_API_KEY` — required; generated via `create_api_key` management command
- `LOG_DB_DISPATCH_URL` — defaults to `http://localhost:8000/add/dispatch/`
- `LOG_DB_ARREST_URL` — defaults to `http://localhost:8000/add/arrest/`

Dispatch CSV columns: `PD Call#`, `Call Start \nDate & Time`, `Call End \nDate & Time`, `Type of Call`, `Street Address / Location`, `Officer Name`

Arrest CSV columns: `Date`, `Arrestee Name`, `Age`, `Home City`, `Charge` (semicolon-separated), `Arrest Type`, `Officer Name`, `Violation Location`
