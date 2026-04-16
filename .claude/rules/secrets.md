---
alwaysApply: true
---

# GnuCash Web — Secrets & Credentials

## No Secrets in Source
- No hardcoded API keys, passwords, tokens, or connection strings in source files
- Use environment variables via `django-environ` for all Django settings
- Stripe secret keys, JWT signing keys, and database credentials must come from environment variables
- Cloudflare R2 credentials (access key, secret key) must come from environment variables
- OCR provider API keys (AWS Textract / Google Vision) must come from environment variables

## .gitignore Rules
- `.env`, `.env.*`, `*.env` files must be in `.gitignore`
- Do not commit `.env.example` with real values — use placeholder values only
- Do not commit Stripe webhook signing secrets, even redacted

## Token Handling
- JWT secret key must be rotated — never hardcode it
- Refresh tokens stored in HttpOnly cookies with `Secure` and `SameSite=Strict` flags
- 2FA TOTP secrets must be encrypted at rest (Django field-level encryption)

## Secrets Management
- Log statements must never include tokens, passwords, or full credit card numbers
- Audit logs must store IP addresses and user agents but strip authorization headers
- Celery configuration must not embed Redis passwords in broker URL strings in source code

## Sources
# Principles: [Separation of Concerns (configuration is not code), Least Privilege, Defense in Depth]
# Date: 2026-04-16