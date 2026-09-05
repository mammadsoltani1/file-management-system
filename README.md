# FileHub

A self-hosted file management and sharing system built with FastAPI, SQLAlchemy, and PostgreSQL. It provides folders, file uploads, trash/restore, search, file sharing between users, and a small built-in web frontend, all backed by a JSON API with JWT authentication.

This is a personal/portfolio project built to demonstrate backend API design, authentication patterns, and testing practices. It is not hardened for production use (see Notes and Limitations at the end).

## Features

**Authentication**
- Register and log in with email and password
- Short-lived JWT access tokens plus HttpOnly-cookie refresh tokens with rotation and reuse detection
- Log out of the current session, or log out of every session at once
- Email verification (sent via Resend)

**Folders and files**
- Create, rename, move, and recursively delete folders
- Upload, download, rename, move, and copy files
- Bulk move, copy, and delete for multiple files at once
- Paginated directory listing

**Trash**
- Deleting a file or folder soft-deletes it into the trash instead of removing it immediately
- Restore a trashed batch, or permanently purge it
- Recursive folder deletes and bulk operations are grouped into a single trash batch so they can be restored or purged together

**Search**
- Case-insensitive filename search across folders and files, paginated

**Sharing**
- Share a file with another registered user by email
- List or revoke the people a file is shared with
- Recipients can list and download files that have been shared with them

**Frontend**
- A minimal HTML/CSS/vanilla JavaScript single-page frontend is served directly by the API (no build step, no framework) covering every feature above

## Tech stack

- **Language / runtime:** Python 3.11+
- **Web framework:** FastAPI (async), Uvicorn
- **ORM / migrations:** SQLAlchemy 2.0 (async), Alembic
- **Databases:** PostgreSQL (Docker), SQLite (local development and tests)
- **Auth:** PyJWT, passlib/bcrypt
- **Email:** Resend (transactional email API)
- **Testing:** pytest, pytest-asyncio, FastAPI's TestClient
- **Linting/formatting:** ruff
- **Packaging:** uv
- **Containerization:** Docker, Docker Compose

## Project structure

```
app/
  api/v1/          route handlers (auth, users, folders, files, trash, search, shares)
  core/            settings and security helpers (password hashing, JWT)
  db/              SQLAlchemy base class and session management
  models/          SQLAlchemy ORM models
  repositories/    database access layer, one repository per model
  schemas/         Pydantic request/response models
  services/        business logic, orchestrates repositories and storage
  storage/         storage provider abstraction (local disk implementation)
  main.py          FastAPI app instance, static frontend mount, health check

alembic/
  versions/        database migrations

frontend/
  index.html       single-page frontend shell
  app.js           frontend logic (auth, browsing, sharing, trash, search)
  style.css        styling

tests/
  api/             one test module per feature area, using an in-memory
                   SQLite database and a temporary storage directory

Dockerfile
docker-compose.yml
pyproject.toml
```

## Getting started

### Option 1: Docker Compose (recommended)

This runs the API against PostgreSQL and requires no local Python setup.

```
cp .env.docker.example .env.docker
docker compose up --build
```

The API is then available at `http://localhost:8000`, with the frontend served at `http://localhost:8000/` and interactive API docs at `http://localhost:8000/docs`.

Database migrations run against the containerized Postgres database with:

```
docker compose exec api uv run --no-sync alembic upgrade head
```

### Option 2: Local development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

By default, local development uses a SQLite database file (`filehub.db`) instead of PostgreSQL.

## Configuration

Configuration is read from environment variables (see `.env.example` and `.env.docker.example` for the full list, and `app/core/config.py` for how they are consumed). Key settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy async database URL (SQLite or PostgreSQL) |
| `SECRET_KEY` | Signing key for JWT access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `STORAGE_PROVIDER` / `LOCAL_STORAGE_PATH` | Where uploaded file content is stored |
| `MAX_UPLOAD_SIZE_BYTES` | Per-file upload size limit |
| `RESEND_API_KEY` / `EMAIL_FROM_ADDRESS` | Transactional email delivery for verification emails |

Never commit real secrets in `.env` or `.env.docker`; both are gitignored.

## Running tests

```
uv run pytest
```

Tests run against an isolated in-memory SQLite database and a temporary upload directory created per test, so they do not touch your development database or `data/uploads`.

## Linting and formatting

```
uv run ruff check .
uv run ruff format .
```

## Database migrations

Migrations are managed with Alembic. After changing a model:

```
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

When running via Docker Compose, apply migrations inside the container instead, since it uses its own PostgreSQL database:

```
docker compose exec api uv run --no-sync alembic upgrade head
```

## API documentation

Once the server is running, interactive API documentation is available at `/docs` (Swagger UI) and `/redoc`.

## Notes and limitations

This project prioritizes demonstrating clean API design, auth, and test coverage over production readiness. Specifically:

- There is no rate limiting or per-user storage quota.
- Email delivery uses Resend's sandbox sender by default, which only reliably delivers to the account owner's own verified email address; verification emails will not reach arbitrary recipients until a custom domain is configured with Resend.
- The local storage provider stores file content on disk under `LOCAL_STORAGE_PATH`; it is not designed for multi-instance deployments.
