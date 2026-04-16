# Log DB Tool

A Django web application for storing and searching police log records (dispatch calls and arrests) from Portland, Maine PD. Includes a CSV ingestion tool for bulk loading data from public records exports.

## Features

- Search police logs by date range, officer, charge, arrest type, address, or record type
- View individual dispatch call details
- Ingest dispatch and arrest records from CSV files via a command-line loader
- Django admin interface for managing lookup data
- Docker-based production deployment with PostgreSQL

## Requirements

- Python 3.8+
- Docker and Docker Compose (for production)

## Local Development Setup

1. Clone the repo and install dependencies:

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

## Production Deployment

Production runs with PostgreSQL via Docker Compose. Configure `stack.env` with the required variables (see `example.env`), then:

```bash
docker-compose up --build
```

## API Key Authentication

The CSV loader authenticates to the Django ingest endpoints using an API key. Keys are generated server-side and never stored in plaintext — only a SHA-256 hash is kept.

**Generate a key** (run from `webproject/`):

```bash
python manage.py create_api_key --name "csv_loader"
```

The raw key is printed once and cannot be recovered. Store it immediately. Keys can be deactivated at any time via the Django admin under **API Keys**.

## Loading CSV Data

The `csv_loader/loader.py` script reads CSV exports and POSTs records to the running Django app. An API key is required (see above).

```bash
export LOG_DB_API_KEY=<key from create_api_key>

# Load a single dispatch CSV
python csv_loader/loader.py -f <file.csv> -m

# Load a single arrest CSV
python csv_loader/loader.py -f <file.csv> -a

# Load a directory of dispatch CSVs
python csv_loader/loader.py -d <directory/> -m
```

The loader reads its target URLs from environment variables, defaulting to localhost:

| Variable | Default |
|----------|---------|
| `LOG_DB_API_KEY` | *(required)* |
| `LOG_DB_DISPATCH_URL` | `http://localhost:8000/add/dispatch/` |
| `LOG_DB_ARREST_URL` | `http://localhost:8000/add/arrest/` |

**Dispatch CSV columns:** `PD Call#`, `Call Start Date & Time`, `Call End Date & Time`, `Type of Call`, `Street Address / Location`, `Officer Name`

**Arrest CSV columns:** `Date`, `Arrestee Name`, `Age`, `Home City`, `Charge`, `Arrest Type`, `Officer Name`, `Violation Location`

## Project Structure

```
webproject/          # Django project
  log_site/          # Settings, root URLs, WSGI
  log_query_site/    # Main app: models, views, templates

csv_loader/          # Standalone CSV ingestion script
Dockerfile
docker-compose.yml
```
