# Deokive Server

FastAPI backend for Deokive. This server is ready for a small public board
deployment on Render with Neon Postgres.

## Stack

- FastAPI
- SQLAlchemy
- JWT auth
- SQLite for local dev
- Postgres for hosted deployment

## Local run

1. Create a virtual environment.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`
4. Optionally set the sole admin account in `.env`
5. `python init_sqlite_db.py`
6. `python make_admin.py`
7. `uvicorn app.main:app --reload`

## Render + Neon

1. Create a free Neon Postgres project.
2. Copy the Neon connection string.
3. Create a new Render Web Service from this repo.
4. Render can use the repo-root `render.yaml`, or set `Root Directory = server`
   manually in the dashboard flow.
5. Set these env vars in Render:
   - `DATABASE_URL`
   - `SOLE_ADMIN_LOGIN_ID`
   - `SOLE_ADMIN_PASSWORD`
   - `SOLE_ADMIN_NICKNAME`
6. Deploy. On startup the app will:
   - create tables
   - ensure the configured admin account exists
   - demote every other account from admin

## Sole admin policy

- Only `SOLE_ADMIN_LOGIN_ID` can use admin-only web/API actions.
- Any other account is treated as a normal user even if `users.is_admin` was
  previously true.

## Basic routes

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `GET /admin`
- `GET /board/posts`
