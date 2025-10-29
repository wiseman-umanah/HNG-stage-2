# Country Currency & Exchange API

A FastAPI back end that caches country metadata along with USD exchange rates, computes an estimated GDP figure, and serves the data from a relational database. The implementation follows the Stage 2 specification: refresh from external services on demand, expose CRUD/status endpoints, and generate a summary image.

## Features

- `POST /countries/refresh` fetches all countries from the REST Countries API, syncs USD exchange rates, performs upserts, and generates a summary image.
- `GET /countries` returns cached countries with optional `region`, `currency`, and GDP sorting filters.
- `GET /countries/{name}` retrieves a single record; `DELETE /countries/{name}` removes it.
- `GET /status` reports total countries plus the most recent refresh timestamp.
- `GET /countries/image` serves the generated snapshot (`cache/summary.png`).
- Consistent JSON error responses and graceful handling of upstream API failures.

## Prerequisites

- Python 3.11+ (tested with 3.13)
- SQLite (default) or a compatible database reachable via SQLModel/SQLAlchemy

## Local Setup

```bash
git clone <repo-url>
cd <repo>/stage_2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install fastapi uvicorn sqlmodel sqlalchemy requests python-dotenv pillow
# add other tooling (pytest, httpx, etc.) as desired
```

Create a `.env` file in `stage_2/`:

```
DB_URL=sqlite:///./countries.db
```

- The SQLite fallback is safe to keep; adjust to your MySQL DSN (e.g. `mysql+pymysql://user:pass@host/dbname`) for production.

Run database migrations (auto-creates on startup) and launch the API:

```bash
uvicorn main:app --reload
```

## Usage

1. Trigger a refresh to cache data:

   ```bash
   curl -X POST http://127.0.0.1:8000/countries/refresh
   ```

   On success you receive counts for created/updated rows; the summary image is saved to `stage_2/cache/summary.png`.

2. Browse countries:

   ```bash
   curl "http://127.0.0.1:8000/countries?region=Africa&sort=gdp_desc"
   ```

3. View a single entry:

   ```bash
   curl http://127.0.0.1:8000/countries/Nigeria
   ```

4. Download the image:

   ```bash
   curl -o summary.png http://127.0.0.1:8000/countries/image
   ```

## Environment & Configuration

- `DB_URL` – SQLAlchemy connection string (default SQLite file).
- Optional: adjust logging via `LOG_LEVEL` (handled by Uvicorn/FastAPI).
- Cached image lives at `stage_2/cache/summary.png`.

## Testing & Validation

- The project currently uses `python -m compileall stage_2` as a quick syntax smoke test.
- Suggested additions:
  - Write unit tests around the refresh service (mock external APIs).
  - Integration tests using `httpx.AsyncClient` against a temporary SQLite database.
  - Add pre-commit hooks for formatting (e.g., black, isort, flake8).

## Deployment Notes

- The app is framework-agnostic; host via services like Railway, Render-alternatives, AWS, etc. (Vercel forbidden per brief).
- Remember to expose the FastAPI app (`stage_2.main:app`) and set environment variables in the hosting platform.
- Configure persistent storage for the database and cache directory if the platform uses ephemeral filesystems.

## API Reference (Quick)

| Method | Path                  | Description                                      |
| ------ | --------------------- | ------------------------------------------------ |
| POST   | `/countries/refresh`  | Fetch latest data from upstream and cache.       |
| GET    | `/countries`          | List cached countries with filters/sorting.      |
| GET    | `/countries/{name}`   | Retrieve a single country by name.               |
| DELETE | `/countries/{name}`   | Delete a country record.                         |
| GET    | `/status`             | Totals + last refresh timestamp.                 |
| GET    | `/countries/image`    | Generated summary image.                         |

All responses are JSON except `/countries/image`, which serves PNG bytes.

## Known Gaps / Next Steps

- Add retry/backoff logic for external API calls.
- Persist a refresh audit trail (per run metadata).
- Harden validation, e.g., schema-based checks for external API payload changes.

Happy hacking! Pull requests and extensions welcome.  If you ship this publicly, remember to include your deployment instructions and API documentation alongside the repo link. 
