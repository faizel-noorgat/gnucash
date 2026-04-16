---
glob: "{Dockerfile*,docker-compose*}"
---

# Infrastructure — Docker Rules

## Dockerfile Structure
- Separate Dockerfiles per service: `Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.admin`
- Use multi-stage builds — one stage for building, one for running — to minimize image size
- Backend: use `python:3.12-slim` as base image — not `python:3.12` (full)
- Frontend/Admin: use `node:20-alpine` for build stage, `nginx:alpine` for serving stage

## Backend Dockerfile
- Install Python dependencies via `pip install --no-cache-dir`
- Use `gunicorn` as the WSGI server — not `manage.py runserver`
- Gunicorn config via `gunicorn.conf.py` — not command-line flags
- Collect static files as a build step — do not serve static files via Django in production

## Frontend Dockerfile
- Build via `npm run build` (Vite) — not `npm start` or `npm run dev`
- Serve built assets via Nginx — not a Node.js server
- Nginx config serves `index.html` for SPA routing (fallback to `/index.html`)
- Enable gzip compression for all asset types in Nginx config

## Docker Compose
- `docker-compose.yml` for local development only — not for production
- Services: `db` (PostgreSQL), `redis` (cache/broker), `backend` (Django), `celery` (worker), `frontend` (Vite dev server)
- Use `.env` file for environment variables — not hardcoded in `docker-compose.yml`
- Database data persisted via named volumes — not bind mounts for production

## Security
- No secrets in Dockerfiles — use build args or runtime environment variables
- Run containers as non-root user — add `USER` directive
- Do not expose database or Redis ports to the host — only the web server port

## Sources
# Principles: [Minimal Attack Surface, Immutable Images, Separation of Concerns (build vs runtime)]
# Web: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
# Date: 2026-04-16