# Test Strategy — TaskTrack QA Suite

## Purpose

This repository is both a **system under test** (TaskTrack) and a **portfolio-grade automation suite**. The strategy favors a testing pyramid: many fast API/contract checks, fewer UI end-to-end flows, with auth/isolation handled at the cheapest reliable layer.

## Layers

| Layer | Location | Transport | What it proves |
| --- | --- | --- | --- |
| **Contract** | `tests/contract/` | In-process TestClient | OpenAPI document validity; key responses match component schemas |
| **API** | `tests/api/` | In-process TestClient | Business rules, validation, authz matrix, pagination/filter |
| **UI** | `tests/ui/` | Live Uvicorn + Playwright | Browser-critical paths; page objects; failure screenshots/traces |

### Why API is in-process

API tests use FastAPI/`starlette.testclient.TestClient` against the ASGI app with a **per-test SQLite file**. That removes:

- Subprocess server flakiness for pure API cases
- Port collisions
- Cross-test data bleed without network reset latency

The test-only reset endpoint (`POST /api/test/reset`) is still exercised and is **gated** to `APP_ENV=test` (404 otherwise).

### Why UI still uses a live server

HTML form posts, cookies, and Playwright need a real HTTP origin. The UI server starts once per session (`APP_ENV=test`), and each UI test resets data via the network API client.

## Isolation model

1. **API/contract:** `isolated_db` reconfigures SQLite to a `tmp_path` file and reseeds.
2. **UI:** session-scoped live server + per-test `live_api.reset_data()`.
3. Seeded users/tasks are deterministic (`alice`, `bob`, `admin` + four tasks).

## Auth bootstrap

| Suite | Auth approach |
| --- | --- |
| API | `ApiClient.as_user("alice")` factory — independent tokens per client |
| UI login tests | Real form login (covers the login path itself) |
| UI task tests | Cookie injection from API-issued token (`authenticated_page` / `admin_page`) |

This keeps most UI cases off the slow full-login path while still validating login as a first-class scenario.

## Markers

| Marker | Intent |
| --- | --- |
| `smoke` | Small PR gate (API + one UI happy path) |
| `api` / `contract` / `ui` | Layer selection |
| `authz` | Role/ownership matrix |
| `regression` | Broader happy-path lifecycle |

## What is *not* automated here

- Load / performance under concurrency
- Cross-browser matrix (Chromium only in CI)
- Cryptographic penetration testing (tokens are opaque random strings, not JWTs — documented residual risk)
- Mobile / accessibility audits beyond basic roles on alerts

## Defect handling

Real findings (or fixed regressions with regression locks) live under `reports/`. Staged “demo-only defects” that simply restated intentional demo shortcuts are avoided; known design limits are documented honestly in the README and defect notes.
