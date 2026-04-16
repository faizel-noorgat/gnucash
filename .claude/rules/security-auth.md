---
glob: "backend/{tenants,gnucash_web}/**/*.{py}"
---

# Security — Auth & Permissions Rules

## Authentication
- Use JWT access tokens with 15-minute expiry — short-lived tokens limit damage from theft
- Use refresh tokens with 7-day expiry stored in HttpOnly, Secure, SameSite=Strict cookies
- Password hashing via Argon2 — never MD5, SHA, or bcrypt
- 2FA via TOTP (Google Authenticator / Authy compatible) — required for all production tenants
- Social login (Google, Apple, Microsoft) via Django Allauth — do not implement OAuth flows manually

## Authorization
- Tenant isolation enforced at ORM layer via `django-multitenant` — every query scoped to `current_tenant`
- PostgreSQL Row Level Security as defense in depth — policies on every tenant-scoped table
- Permission checks on all API endpoints via DRF `permission_classes` — never rely on URL obscurity
- Admin hub endpoints require `IsAdminUser` or custom `IsPlatformAdmin` permission — tenant members cannot access admin endpoints

## Token Handling
- JWT secret key must be a minimum of 256 bits, sourced from environment variable
- Token blacklisting on logout — use `djangorestframework-simplejwt` token blacklist
- Refresh token rotation — issuing a new refresh token invalidates the old one
- Session revocation: users can revoke individual devices by deleting their refresh tokens

## Security Controls
- Rate limiting on login attempts — max 5 attempts per 15 minutes per IP
- Account lockout after 10 consecutive failed attempts — unlock via email verification
- Password strength: minimum 12 characters, must contain uppercase, lowercase, number, and special character
- Do not log passwords, tokens, or full credit card numbers

## Audit Events
- Log login, logout, failed login, password change, 2FA enable/disable events in `AuditLog`
- Audit log entries are immutable — `AuditLog` model has no delete or update endpoints
- Cross-tenant audit log accessible only from admin hub with platform admin permissions

## Sources
# Principles: [Separation of Concerns (auth logic is never mixed into business logic), Least Privilege, Defense in Depth]
# Web: https://www.django-rest-framework.org/api-guide/permissions/
# Web: https://django-allauth.readthedocs.io/
# Web: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
# Date: 2026-04-16