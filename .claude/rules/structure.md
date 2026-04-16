---
alwaysApply: true
---

# GnuCash Web — Structural Rules

## Project Structure
- Backend Django apps live under `backend/<app_name>/` — each app is a self-contained domain (accounts, transactions, budgets, etc.)
- Two separate React apps: `frontend/` (tenant-facing) and `admin/` (admin hub) — never share source between them
- Shared utilities between frontend and admin must be extracted to a separate package, not copied
- Docker configurations live at the repo root (`Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.admin`)
- `docker-compose.yml` at repo root for local development only

## Code Organization
- One Django app per bounded context — do not add models for unrelated domains to the same app
- Frontend feature modules live under `frontend/src/features/<feature>/` — co-locate components, hooks, and types per feature
- Admin hub mirrors tenant app structure under `admin/src/features/<feature>/`
- Custom Zustand stores live under `frontend/src/stores/` and `admin/src/stores/`
- Custom React hooks live under `frontend/src/hooks/` and `admin/src/hooks/`
- Shared shadcn/ui components live under `frontend/src/components/ui/` and `admin/src/components/ui/`

## Naming Conventions
- Django apps: lowercase, no underscores (e.g., `transactions`, not `Transactions` or `transaction_mgmt`)
- Python modules: snake_case
- Python classes: PascalCase
- React components: PascalCase
- TypeScript types/interfaces: PascalCase, prefixed with `I` only for interfaces that represent external contracts
- CSS/Tailwind: use kebab-case for custom class names, utility classes only for shadcn components
- API URLs: kebab-case in path segments, versioned under `/api/v1/`

## Git & Commits
- Conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`
- One logical change per commit — do not mix refactors with feature work
- Migration files must be committed with the model changes that generated them

## CI/CD
- GitHub Actions workflow files live under `.github/workflows/`
- Automated testing runs on every PR
- Deploy on merge to main
- Database migrations run as a separate CI step before deploy

## Sources
# Principles: [Separation of Concerns, Convention over Configuration, Bounded Contexts (DDD)]
# Date: 2026-04-16