---
glob: ".github/workflows/**/*.{yml,yaml}"
---

# CI/CD — GitHub Actions Rules

## Workflow Structure
- Separate workflow files by concern: `ci.yml` (tests), `deploy.yml` (deployment), `migrations.yml` (database migrations)
- All workflows triggered by `push` to `main` or `pull_request` to `main`
- Use reusable workflows for shared steps (e.g., `setup-python`, `setup-node`)

## CI Workflow
- Run on every PR — must pass before merge
- Lint: Python (`ruff` or `flake8`), TypeScript (`tsc --noEmit`, `eslint`)
- Test: `pytest` with coverage threshold (80% backend), `vitest` for frontend (70%)
- Type check: `mypy` for backend, `tsc` for frontend
- No deployment steps in CI workflow — only verification

## Deploy Workflow
- Triggered on merge to `main`
- Steps: build Docker images, push to registry, run database migrations, deploy app containers
- Database migrations run as a separate step BEFORE app deployment — never after
- Deploy uses SSH or Docker Compose — no manual server commands in workflows

## Secrets in Workflows
- Use GitHub Secrets for all sensitive values — never hardcode in workflow files
- Required secrets: database credentials, Stripe keys, JWT secret, Cloudflare R2 credentials
- Use OIDC for cloud provider authentication where possible — avoid long-lived credentials

## Environment Protection
- Use GitHub Environments (`staging`, `production`) with required reviewers for production deploys
- Branch protection rules on `main` — require CI workflow to pass, require at least one review
- No force pushes to `main`

## Sources
# Principles: [Automation First, Fail Fast, Immutable Infrastructure]
# Web: https://docs.github.com/en/actions
# Date: 2026-04-16