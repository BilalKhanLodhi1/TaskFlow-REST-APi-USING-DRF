# TaskFlow API

A project and team collaboration REST API (inspired by Jira, Trello and Asana),
built with Django 5.2 LTS and Django REST Framework.

> **Status:** Phase 1 of 12 complete — project skeleton, configuration,
> health check, API docs and test setup. This README grows with each phase.

## Tech stack

Python 3.12 · Django 5.2 LTS · Django REST Framework · Simple JWT · django-filter ·
django-cors-headers · drf-spectacular · PostgreSQL (SQLite for local learning) ·
pytest · Gunicorn

## Project structure

```
taskflow-api/
├── config/          # settings, root URLs, WSGI/ASGI entry points
├── apps/
│   ├── common/      # shared pagination, permissions, utilities, health check
│   ├── accounts/    # custom user model, registration, JWT auth (Phase 2)
│   ├── projects/    # projects, membership, roles (Phases 3–4)
│   ├── tasks/       # task lifecycle, assignment, filtering (Phases 5–6)
│   ├── comments/    # task discussions (Phase 7)
│   ├── attachments/ # secure file uploads (Phase 7)
│   ├── notifications/ # in-app notifications (Phase 8)
│   └── activity/    # audit trail (Phase 8)
└── tests/           # pytest test suite
```

## Local setup (macOS)

Prerequisites: Homebrew and Python 3.12 (`brew install python@3.12`).

```bash
cd taskflow-api
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt

cp .env.example .env
# Put a real secret key into .env:
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"

python manage.py check
pytest
python manage.py runserver
```

> ⚠️ Do **not** run `python manage.py migrate` until Phase 2 has added the
> custom user model. Changing the user model after the first migration is
> painful and usually requires resetting the database.

## Available endpoints (so far)

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| GET | `/api/v1/health/` | None | Liveness check |
| GET | `/api/schema/` | None | OpenAPI 3 schema |
| GET | `/api/docs/` | None | Swagger UI |
| GET | `/api/redoc/` | None | ReDoc |

## Running tests

```bash
pytest                          # whole suite
pytest tests/test_setup.py      # one module
pytest -k health                # tests whose name contains "health"
```

## Security notes

- Secrets come only from environment variables; `.env` is git-ignored.
- `DJANGO_DEBUG` defaults to `False`, and the app refuses to start in
  production mode without `DJANGO_SECRET_KEY`.
- Every API endpoint requires authentication unless it explicitly opts out.
- HTTPS redirect, secure cookies and HSTS activate automatically when
  `DJANGO_DEBUG=False`.
