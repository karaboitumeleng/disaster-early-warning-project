# Security: threat model and controls

Scope: the local prototype, built as if it will be exposed. "Implemented" means code exists; it has
not been penetration-tested. Items under "Gaps" are NOT done.

## Assets
Alert integrity (a forged or suppressed alert has real-world consequences), account credentials,
the audit trail, model artefacts, and data feeds,
Weather/hydro readings, alerts, audit log, user credentials, model artefacts.

## Threats and controls (STRIDE-style)

| Threat | Control | Status |
|---|---|---|
| Unauthenticated access | JWT (HS256, expiry) required on every route except login and health | Implemented |
| Privilege misuse | Roles: admin / analyst / viewer; viewers are read-only; only admin can simulate feed outages | Implemented |
| Credential guessing | bcrypt hashes, per-IP login rate limit (in-memory), constant-time-ish path for unknown users | Implemented |
| Injection | SQLAlchemy ORM only; Pydantic validation; ID fields restricted to a safe character set | Implemented |
| Malformed or malicious payloads | Coordinate and range validation (South Africa bounding box), future-timestamp rejection, request size cap | Implemented |
| Duplicate or replayed sensor data | SHA-256 payload hash as idempotency key; one alert per reading | Implemented |
| XSS | React escaping, no raw HTML injection; map markers built with textContent | Implemented |
| Token theft from browser storage | Token held in memory only (refresh signs out) | Implemented |
| Clickjacking / sniffing | X-Frame-Options, nosniff, CSP on API responses, restrictive CORS | Implemented |
| Repudiation | Audit log: logins, ingests, predictions, alerts, status changes, feed simulation | Implemented |
| Secret leakage | Secrets only via environment / .env (git-ignored); app refuses to start without JWT_SECRET | Implemented |
| Information disclosure via errors | Global handler returns a generic error; stack traces stay in logs | Implemented |
| Availability / dependency failure | Circuit breaker + retries, graceful degradation, isolated event handlers | Implemented (no live external client yet) |
| Unauthorised API access | JWT bearer auth on every route except `/health*` and `/auth/login`; RBAC (admin/analyst/viewer) | `api/deps.py`, `security.py` |
| Credential stuffing / brute force | Sliding-window rate limiter on login (10/min/IP); constant-time-ish check via dummy hash for unknown usernames | `security.py`, `routes.login` |
| Password compromise | bcrypt, no plaintext ever stored or logged | `security.py` |
| Token forgery/replay | HS256 JWT, server-side secret ≥32 chars enforced at startup, short expiry (60 min default) | `config.py`, `security.py` |
| Malformed/oversized input | Pydantic validation on every field (SA bounding box, physical ranges); request body size guard | `schemas.py`, `main.py` middleware |
| SQL injection | SQLAlchemy ORM only, no raw string SQL anywhere in the app layer | `repositories.py` |
| XSS | React escapes all rendered content by default; no `dangerouslySetInnerHTML` used anywhere | `frontend/src` |
| CSRF | No cookie-based auth (bearer token in memory only); CORS restricted to configured origins | `main.py` |
| Clickjacking / MIME sniffing | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, restrictive CSP | `main.py` middleware |
| WebSocket hijack | Origin check + token required as the first message (not in the URL, so it never lands in logs) | `routes.ws_alerts` |
| Tampered dataset | SHA-256 checksums recorded for every raw/processed artefact | `notebooks/01`, `02`, `03` |
| Stack traces leaking to clients | Global exception handler returns `{"error": "internal_error"}`; full trace only in server logs | `main.py` |
| No accountability for actions | Every login, ingest, prediction, and alert transition is written to `audit_log` with actor + timestamp | `repositories.AuditRepo` |
| Secrets in the repo | `.env` is git-ignored; only `.env.example` (no real values) is committed | `.gitignore`, `.env.example` |


## Gaps (honest list)
- No TLS: put a reverse proxy in front for any non-local use.
- No refresh tokens or token revocation; the JWT secret is symmetric.
- Rate limiter is per-process memory (no shared store, no account lockout).
- Audit log is not tamper-evident (no hash chaining, same database as the data).
- SQLite is unencrypted; no backups.
- No uploaded-file endpoint exists yet, so file-upload sanitisation is untested.
- No dependency scanning or pen test; `mypy`, `ruff` and `black` have not been run on this code.
- The WebSocket authenticates with the first message; there is no per-message re-authentication.
