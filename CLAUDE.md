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
python manage.py geocode_records        # Bulk-geocode un-geocoded records
python manage.py geocode_records --limit 100  # Process only first N records
```

For local async geocoding, also run:

```bash
redis-server
celery -A log_site worker --loglevel=info --concurrency=1
```

## Production / Docker

```bash
docker-compose up --build   # Run from repo root; starts db, redis, backend, celery
```

- Dev: SQLite (`db.sqlite3`), settings in `webproject/log_site/settings.py`
- Prod: PostgreSQL via Docker, settings in `webproject/log_site/production.py`

Production reads `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `CELERY_BROKER_URL` from `stack.env`.

## Architecture

```
webproject/
  log_site/          # Django project package (settings, urls, wsgi, celery)
    settings.py      # Dev settings (SQLite, DEBUG=True)
    production.py    # Production settings (PostgreSQL)
    celery.py        # Celery app instance
    urls.py          # Root URL config
  log_query_site/    # Single main Django app
    models.py        # All data models + record creation logic
    views.py         # All views (search, add, about, geocode trigger)
    reports.py       # Report views (activity, gaps, ungeocoded, queue)
    auth.py          # require_api_key decorator for ingest endpoints
    geocoder.py      # Nominatim geocoding helper; raises GeocoderUnavailable / GeocoderRateLimited
    geocoder_control.py  # Pause/resume flag stored in Redis
    tasks.py         # Celery task: geocode_record
    admin.py         # Admin registrations
    templates/       # HTML templates (base.html + per-view)
    management/commands/
      create_api_key.py   # API key generation
      geocode_records.py  # Bulk geocoding with rate-limit sleep

csv_loader/
  loader.py          # CLI script: reads CSV, POSTs JSON to Django API
```

### Data Model

`PoliceLog` is the central model with two record types (dispatch / arrest), referencing lookup tables:
- **Dispatch**: `DispatchType`, `Disposition`, `Officer`
- **Arrest**: `Arrestee`, `ArrestType`, `Charge` (M2M), `Officer`
- Both: `Municipality`, `RecordType`
- Coordinates: `latitude`, `longitude` (nullable FloatField, populated by Celery task)

All lookup models implement a `get_or_create` / `search_by_name` / `create` class-method pattern to deduplicate entries on ingest.

All string fields normalise whitespace on ingest with `' '.join(value.split())` to handle CSV fields that contain embedded newlines.

`APIKey` stores hashed API keys (SHA-256). Only the prefix (first 8 chars) and hash are stored — the raw key is shown once at creation.

`RecordType` rows (`Dispatch`, `Arrest`) are seeded by migration `0006_seed_record_types` and must exist before ingesting records.

`Municipality` rows must be pre-loaded (e.g., `PWM` / Portland). Currently loaded via Django admin or shell.

### Duplicate dispatch_number handling

On `IntegrityError` from a duplicate `dispatch_number`:
- If the existing record has the same `datetime_start` and `address` → true duplicate, return existing record
- Otherwise → different record with a colliding number; offset by 100 000 (repeating) until a unique slot is found

### Geocoding

- `geocode_record` Celery task fires on every ingest via `.delay(record.id)`
- Before calling Nominatim, checks if another record at the same address already has coordinates and reuses them
- Rate limited to `1/s`; worker runs `--concurrency=1`
- On HTTP 429: retries once after 600 s, then logs error and drops
- On network error: retries up to 5× with 120 s delay
- On no result (address not found): drops silently, record stays un-geocoded
- Pause/resume flag stored as `geocoder:paused` key in Redis via `geocoder_control.py`
- If broker unavailable at ingest time, `.delay()` is wrapped in try/except — record saves successfully, geocoding is deferred

### Key URL Routes

| Route | Purpose |
|-------|---------|
| `GET /` | Home page |
| `GET /about/` | Stats / metadata |
| `GET /search/` | Search form |
| `POST /results/` | Execute query (paginated, default 100/page) |
| `POST /results/export/` | CSV export of current search (no row limit) |
| `POST /records/<id>/geocode/` | Queue geocoding for a single record |
| `POST /geocoder/pause/` | Toggle geocoding pause/resume |
| `POST /add/arrest/` | JSON ingest endpoint (`@csrf_exempt`, `@require_api_key`) |
| `POST /add/dispatch/` | JSON ingest endpoint (`@csrf_exempt`, `@require_api_key`) |
| `GET /reports/` | Reports index |
| `GET /reports/activity/` | Activity bar charts |
| `GET /reports/data-gaps/` | Data gap analysis |
| `GET /reports/ungeocoded/` | Un-geocoded records list |
| `GET /reports/geocode-queue/` | Celery queue status + pause/resume |

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

CSV fields may contain embedded newlines (multiline quoted cells); all are normalised before storage.
