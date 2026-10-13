# Security: threat model and controls

Scope: the local prototype, built as if it will be exposed. "Implemented" means code exists; it has
not been penetration-tested. Items under "Gaps" are NOT done.

## Assets
Alert integrity (a forged or suppressed alert has real-world consequences), account credentials,
the audit trail, model artefacts, and data feeds.

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

## Gaps (honest list)
- No TLS: put a reverse proxy in front for any non-local use.
- No refresh tokens or token revocation; the JWT secret is symmetric.
- Rate limiter is per-process memory (no shared store, no account lockout).
- Audit log is not tamper-evident (no hash chaining, same database as the data).
- SQLite is unencrypted; no backups.
- No uploaded-file endpoint exists yet, so file-upload sanitisation is untested.
- No dependency scanning or pen test; `mypy`, `ruff` and `black` have not been run on this code.
- The WebSocket authenticates with the first message; there is no per-message re-authentication.
