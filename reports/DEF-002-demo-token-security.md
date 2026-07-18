# DEF-002 — Residual risk: session tokens are opaque, not signed JWTs

| Field | Value |
| --- | --- |
| **ID** | DEF-002 |
| **Title** | Auth uses opaque server-side session tokens (acceptable residual risk for this SUT) |
| **Severity** | Informational for this demo; would be design review item for production |
| **Priority** | P3 (portfolio SUT) |
| **Status** | **Accepted residual risk** — partially mitigated vs v1 |
| **Environment** | TaskTrack 2.0.0 |
| **Component** | API / Auth |
| **Date found** | 2026-07-18 |

### Summary

TaskTrack v1 used predictable tokens (`tok-{user_id}-{timestamp}`) and **plaintext passwords**. Those were real defects for anything beyond a toy.

### Mitigations shipped in v2

| Risk | v1 | v2 |
| --- | --- | --- |
| Password storage | Plaintext compare | PBKDF2-SHA256 hashes (`app/auth.py`) |
| Token predictability | User-id + timestamp prefix | `secrets.token_urlsafe(32)` opaque tokens |
| Test reset exposure | Always registered | **404 unless `APP_ENV=test`** |
| Persistence | In-memory only | SQLite |

### Residual limitations (honest)

- Tokens are **not** JWTs; no built-in expiry claim or signing.
- No refresh-token rotation, CSRF double-submit, or HTTPS-only cookie flags beyond `httponly` + `samesite=lax`.
- PBKDF2 iteration count is tunable via `TASKTRACK_PBKDF2_ITERATIONS` (suite lowers it for speed).

### Regression locks

- `tests/api/test_auth.py::test_passwords_are_hashed_not_plaintext`
- `tests/api/test_auth.py::test_tokens_are_opaque`
- `tests/api/test_reset_gate.py` (reset gated)

### Why not “fixed” to JWT

The project’s primary product is the **automation suite**, not a production IdP. Opaque server-side tokens are adequate for a multi-role SUT while keeping the auth path simple to exercise in API and UI tests.
