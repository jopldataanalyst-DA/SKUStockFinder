# Deploying on Dokploy (Nixpacks)

This repo has two independently deployable services. Create two separate
Dokploy applications from this same git repo, each with a different
**Build Path**, both using the **Nixpacks** builder (each folder has its own
`nixpacks.toml`).

## 1. Backend — `backend/`

- Build path: `backend`
- Builder: Nixpacks (auto-detected via `backend/nixpacks.toml`)
- Exposes: FastAPI on `$PORT` (Dokploy/Nixpacks injects `PORT` automatically)

Environment variables to set in Dokploy (see `backend/.env.example`):

```
DB_HOST=...
DB_PORT=5432
DB_USER=postgres.default
DB_PASSWORD=...
DB_NAME=postgres

UNICOMMERCE_BASE_URL=https://jainam.unicommerce.com
UNICOMMERCE_CLIENT_ID=my-trusted-client
UNICOMMERCE_USERNAME=...
UNICOMMERCE_PASSWORD=...
UNICOMMERCE_FACILITIES=MYNTRAPPMP_NEW1

FETCH_INTERVAL_MINUTES=30
CORS_ORIGINS=https://your-frontend-domain.example
```

Set `CORS_ORIGINS` to the deployed frontend's URL(s), comma-separated.

## 2. Frontend — `frontend/`

- Build path: `frontend`
- Builder: Nixpacks (auto-detected via `frontend/nixpacks.toml`)
- Serves the built static site on `$PORT` via `serve`

Environment variables (these are **build-time** — Vite bakes them into the
bundle, so they must be set as build args/env in Dokploy, not just runtime):

```
VITE_SUPABASE_URL=http://187.127.181.189:8000
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=https://your-backend-domain.example
```

`VITE_API_URL` should point at the deployed backend's public URL.

## Notes

- Both `.env` files are gitignored. Populate the real values directly in
  Dokploy's environment variable settings for each app.
- The backend's Postgres connection goes through Supavisor, so `DB_USER`
  must be tenant-qualified (`postgres.default`) rather than plain `postgres`.
