# DEF-002 — Token format is predictable and not cryptographically signed

| Field | Value |
| --- | --- |
| **ID** | DEF-002 |
| **Title** | Auth tokens are opaque demo strings, not signed JWTs (acceptable only for demo app) |
| **Severity** | Major *(in a production context)* / Informational *(for this demo)* |
| **Priority** | P3 for portfolio demo; would be P0 in production |
| **Status** | Accepted risk — intentional for the system under test |
| **Environment** | TaskTrack 1.0.0 (in-memory demo) |
| **Build / Commit** | initial portfolio release |
| **Component** | API / Auth |
| **Found by** | Security-minded exploratory review of `app/main.py` and `app/database.py` |
| **Date found** | 2026-07-18 |
| **Assignee** | N/A (documented design limitation) |

### Summary
Authentication tokens are generated as `tok-{user_id}-{timestamp}` and stored in an in-memory map. They are not signed, not expiring by policy, and passwords are stored in plain text. This is intentional for a self-contained demo that prioritizes deterministic test data, but it must not be treated as production-safe.

### Steps to Reproduce
1. `POST /api/auth/login` with `{"username":"alice","password":"alice123"}`.
2. Inspect `access_token` in the response body.
3. Observe format: `tok-user-alice-<timestamp>`.
4. Reuse the token on `GET /api/auth/me` successfully.

### Expected Result (production)
- Passwords hashed (e.g. bcrypt/argon2).
- Tokens signed (JWT) or random opaque IDs with server-side session store.
- Expiration, rotation, and HTTPS-only cookies.

### Actual Result (demo)
- Plain-text password comparison.
- Predictable token prefix including user id.
- In-memory only; reset via `/api/test/reset` for test isolation.

### Evidence
- Token creation: `app/database.py` → `create_token`
- Seeded credentials: `alice/alice123`, `bob/bob1234` (documented in README)

### Impact
- **Demo/portfolio:** none — simplifies automation and reproducibility.
- **If mistakenly reused in production:** high security risk (credential theft, session forgery).

### Suggested Fix / Notes
If evolving beyond a SUT demo:
1. Hash passwords at rest.
2. Issue signed JWTs or secure random session tokens.
3. Remove `/api/test/reset` from non-test deployments.
4. Enforce HTTPS and secure cookie flags for the UI session.

### Verification
Documented as known limitation in README. Automated suite continues to validate functional auth behavior (login success/failure, unauthorized access) without treating crypto hardening as in-scope for this demo.
