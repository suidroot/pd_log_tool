# Log DB Tool

A Django web application for storing and searching police log records (dispatch calls and arrests) from Portland, Maine PD. Includes a CSV ingestion tool for bulk loading data from public records exports.

## Features

- Search police logs by date range, officer, charge, arrest type, address, or record type
- Paginated search results with CSV export
- Interactive OpenStreetMap map on search results (for geocoded records)
- Trigger per-record geocoding directly from search results
- Reports: activity charts, data gaps, un-geocoded records, geocode queue status
- Asynchronous geocoding via Celery + Redis with pause/resume control
- Ingest dispatch and arrest records from CSV files via a command-line loader
- Django admin interface for managing lookup data
- Docker-based production deployment with PostgreSQL + Redis

## Requirements

- Python 3.8+
- Docker and Docker Compose (for production)
- Redis (for Celery task queue)

## Loader Modules
Various Police departments have different CMS and file formats and will require different download scripts, these can be added as submodules to the project in the `log_loaders` directory. Below is a list of the known loaders.

- Portland Maine: https://github.com/suidroot/PWM-Police-Log-Downloader.git


## Local Development Setup

1. Clone the repo (including optional submodules) and install dependencies:

   ```bash
   git clone --recurse-submodules <repo-url>
   # or, if already cloned without submodules:
   git submodule update --init
   ```

   Then install Python dependencies:

   ```bash
   pip install -r webproject/requirements.txt
   ```

2. Create a `dev.env` file at the repo root (see `example.env` for required variables), then load it:

   ```bash
   cd webproject
   source load_env.sh
   ```

3. Apply migrations and start the dev server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

   The app will be available at `http://localhost:8000`. Dev mode uses SQLite.

4. Create an admin user:

   ```bash
   python manage.py createsuperuser
   ```

5. For local async geocoding, start Redis and a Celery worker:

   ```bash
   redis-server
   celery -A log_site worker --loglevel=info --concurrency=1
   ```

## Production Deployment

Production runs with PostgreSQL, Redis, and a Celery worker via Docker Compose. Configure `stack.env` with the required variables (see `example.env`), then:

```bash
docker-compose up --build
```

This starts four services: `db` (PostgreSQL), `redis`, `backend` (Django), and `celery` (worker).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | *(required in prod)* | Space-separated allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | *(required in prod)* | Space-separated trusted origins |
| `POSTGRES_DB` | *(required in prod)* | PostgreSQL database name |
| `POSTGRES_USER` | *(required in prod)* | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required in prod)* | PostgreSQL password |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `MAP_TILE_PROVIDER` | `carto-light` | Map tiles: `osm`, `carto-light`, `carto-dark` |
| `LOG_DB_API_KEY` | *(required for loader)* | CSV loader API key |
| `LOG_DB_DISPATCH_URL` | `http://localhost:8000/add/dispatch/` | Dispatch ingest endpoint |
| `LOG_DB_ARREST_URL` | `http://localhost:8000/add/arrest/` | Arrest ingest endpoint |

## API Key Authentication

The CSV loader authenticates to the Django ingest endpoints using an API key. Keys are generated server-side and never stored in plaintext — only a SHA-256 hash is kept.

**Generate a key** (run from `webproject/`):

```bash
python manage.py create_api_key --name "csv_loader"
```

The raw key is printed once and cannot be recovered. Store it immediately. Keys can be deactivated at any time via the Django admin under **API Keys**.

## Loading CSV Data Maunally

The `csv_loader/loader.py` script reads CSV exports and POSTs records to the running Django app. An API key is required (see above). This can be used as template code to use in parsers and downloaders for various police departments reports.

```bash
export LOG_DB_API_KEY=<key from create_api_key>

# Load a single dispatch CSV
python csv_loader/loader.py -f <file.csv> -m

# Load a single arrest CSV
python csv_loader/loader.py -f <file.csv> -a

# Load a directory of dispatch CSVs
python csv_loader/loader.py -d <directory/> -m
```

**Dispatch CSV columns:** `PD Call#`, `Call Start Date & Time`, `Call End Date & Time`, `Type of Call`, `Street Address / Location`, `Officer Name`

**Arrest CSV columns:** `Date`, `Arrestee Name`, `Age`, `Home City`, `Charge` (semicolon-separated), `Arrest Type`, `Officer Name`, `Violation Location`

CSV fields with embedded newlines (common in exported spreadsheets) are normalised automatically on import. All string fields have whitespace collapsed before storage.

**Duplicate dispatch numbers:** if a record arrives with a `dispatch_number` that already exists, the ingest compares `datetime_start` and `address`. A true duplicate is silently skipped; a different record that happens to share the number is inserted with the number offset by 100 000 (repeating until a free slot is found).

## Geocoding

Records are geocoded against the OpenStreetMap Nominatim API to enable the map view on search results. Coordinates are stored as `latitude`/`longitude` on each `PoliceLog` record.

Geocoding happens **automatically and asynchronously** via Celery whenever a new record is ingested. If the queue is unavailable at import time, the record is saved without coordinates and can be geocoded later.

Before calling Nominatim, the task checks whether another record at the same address is already geocoded and reuses those coordinates — minimising API calls. The policies are located at https://operations.osmfoundation.org/policies/nominatim/

**Bulk-geocode existing records** (run from `webproject/`):

```bash
python manage.py geocode_records           # geocode all un-geocoded records
python manage.py geocode_records --limit 100  # process only the first 100
```

**Rate limiting:** Nominatim enforces 1 request/second. The Celery worker runs with `--concurrency=1` and the task has `rate_limit='1/s'`. On HTTP 429, the task retries once after 600 seconds then gives up.

**Pause/resume:** the geocoding queue can be paused and resumed from the Geocode Queue report at `/reports/geocode-queue/` without losing queued tasks.

## Reports

Available at `/reports/`:

| Report | URL | Description |
|--------|-----|-------------|
| Activity Charts | `/reports/activity/` | Bar charts of dispatches or arrests per day over a date range |
| Data Gaps | `/reports/data-gaps/` | Missing days in dispatch/arrest coverage with severity indicators |
| Un-geocoded Records | `/reports/ungeocoded/` | All records lacking map coordinates |
| Geocode Queue | `/reports/geocode-queue/` | Live Celery queue status, worker health, and pause/resume control |

## Project Structure

```
webproject/          # Django project
  log_site/          # Settings, root URLs, WSGI, Celery app
  log_query_site/    # Main app: models, views, reports, templates
    tasks.py         # Celery geocoding task
    geocoder.py      # Nominatim geocoding helper
    geocoder_control.py  # Pause/resume flag (Redis-backed)
    management/commands/
      create_api_key.py   # Generate CSV loader API key
      geocode_records.py  # Bulk geocoding command

csv_loader/          # Standalone CSV ingestion script
Dockerfile
docker-compose.yml
```
