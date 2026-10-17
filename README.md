# TaskFlow API

A project and team collaboration REST API (inspired by Jira, Trello and Asana),
built with Django 5.2 LTS and Django REST Framework.

> **Status:** Phase 2 of 12 complete — project setup, custom email-based
> user model and JWT authentication. This README grows with each phase.

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

python manage.py migrate
python manage.py createsuperuser   # prompts for email and password
pytest
python manage.py runserver
```

Then open http://127.0.0.1:8000/ (redirects to the Swagger docs).

## Available endpoints (so far)

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| GET | `/api/v1/health/` | None | Liveness check |
| POST | `/api/v1/auth/register/` | None | Create an account |
| POST | `/api/v1/auth/token/` | None | Log in, returns `access` + `refresh` |
| POST | `/api/v1/auth/token/refresh/` | None | New tokens from a refresh token |
| POST | `/api/v1/auth/logout/` | Bearer | Revoke a refresh token |
| GET | `/api/v1/auth/me/` | Bearer | Your profile |
| PATCH | `/api/v1/auth/me/` | Bearer | Update first/last name |
| POST | `/api/v1/auth/change-password/` | Bearer | Change password, ends all sessions |
| GET | `/api/schema/` | None | OpenAPI 3 schema |
| GET | `/api/docs/` | None | Swagger UI |
| GET | `/api/redoc/` | None | ReDoc |

## Authentication

TaskFlow uses JWT (JSON Web Tokens):

1. `POST /api/v1/auth/token/` with `{"email": "...", "password": "..."}`.
2. Send the **access** token on every request:
   `Authorization: Bearer <access>`. It expires after 15 minutes.
3. When it expires, `POST /api/v1/auth/token/refresh/` with
   `{"refresh": "<refresh>"}`. You get a new pair; the old refresh token
   is revoked (rotation).
4. To log out, `POST /api/v1/auth/logout/` with the refresh token.

Login, registration, refresh and password change are limited to 10
requests per minute per client.

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
- Emails are unique case-insensitively, enforced by a database constraint.
- Passwords are checked by Django's password validators and stored hashed.
- Login returns the same error for unknown emails and wrong passwords.
- Changing a password revokes every refresh token the user holds.
- HTTPS redirect, secure cookies and HSTS activate automatically when
  `DJANGO_DEBUG=False`.
