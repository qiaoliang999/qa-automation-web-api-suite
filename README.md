# QA Automation Web + API Suite

**Portfolio project — SDET / QA Automation**

Self-contained **TaskTrack** application (system under test) plus a layered **pytest** suite: contract, in-process API, and Playwright UI. Designed to show product-shaped automation engineering rather than a tutorial todo list.

[![CI](https://github.com/qiaoliang999/qa-automation-web-api-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/qiaoliang999/qa-automation-web-api-suite/actions/workflows/ci.yml)

Repository: https://github.com/qiaoliang999/qa-automation-web-api-suite

---

## For hiring managers / reviewers (60 seconds)

**Role signal:** SDET / Automation QA (Web + API)

**What you can verify in this repo:**

- Testing pyramid with clear layer ownership: **contract → API → UI**
- In-process FastAPI tests (TestClient) plus Playwright page objects for browser coverage
- Parametrized role-based authorization matrix (user vs admin, ownership boundaries)
- OpenAPI contract validation and response schema checks
- CI split into lint / API+contract / UI / smoke gates with JUnit + HTML artifacts
- Defect write-ups (fixed regression + residual design risk) alongside the suite

**Start here (3 links):**

1. Test strategy → [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md)
2. CI workflow → [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
3. Sample defect report → [`reports/DEF-001-whitespace-title-validation.md`](reports/DEF-001-whitespace-title-validation.md)

API layer tests: [`tests/api/`](tests/api/) · UI page objects: [`tests/ui/pages/`](tests/ui/pages/)

---

## What this demonstrates

- Testing pyramid: **contract → API → UI**
- In-process FastAPI tests (TestClient), not a subprocess for every API case
- Role-based authorization matrix (user vs admin) with parametrization
- OpenAPI contract checks (`openapi-spec-validator` + response schema validation)
- Factories, multi-user `ApiClient`, page objects, markers
- Cookie-injected UI sessions (API-seeded auth) + targeted real login tests
- Screenshot + Playwright trace on UI failure
- CI split into lint / API+contract / UI / smoke gates with JUnit + HTML artifacts

---

## Tech stack

| Layer | Choice |
| --- | --- |
| SUT | Python 3.12, FastAPI, Jinja2, SQLite, PBKDF2 password hashing |
| API / contract | pytest + FastAPI TestClient + jsonschema + openapi-spec-validator |
| UI | Playwright (Chromium) + Page Object Model |
| Reporting | pytest-html, JUnit XML, screenshots, traces |
| CI | GitHub Actions (parallel-ish jobs; smoke as PR-style gate) |
| Lint | Ruff |

---

## Architecture

```
qa-automation-web-api-suite/
├── app/                         # TaskTrack SUT
│   ├── main.py                  # API + HTML routes
│   ├── models.py                # Pydantic models (roles, priority, due_date, pagination)
│   ├── database.py              # SQLite store + seed/reset
│   ├── auth.py                  # PBKDF2 + opaque tokens
│   ├── templates/               # Login + tasks UI
│   └── static/
├── tests/
│   ├── contract/                # OpenAPI / schema
│   ├── api/                     # In-process API (auth, tasks, authz, reset gate)
│   ├── ui/                      # Playwright + page objects
│   ├── support/                 # ApiClient, factories, config, BasePage
│   └── conftest.py              # Isolation, clients, browser, evidence hooks
├── docs/TEST_STRATEGY.md
├── test-cases/
├── reports/                     # Realistic defect / residual-risk notes
├── .github/workflows/ci.yml
├── pyproject.toml
├── pytest.ini
└── requirements.txt
```

**Isolation**

- API/contract: per-test SQLite file via `TASKTRACK_DB` / `db.reconfigure`.
- UI: one live Uvicorn process (`APP_ENV=test`) + per-test `POST /api/test/reset`.
- Reset endpoint returns **404** unless `APP_ENV=test`.

---

## Product under test: TaskTrack v2

### Seeded accounts

| Username | Password | Role |
| --- | --- | --- |
| `alice` | `alice123` | user |
| `bob` | `bob1234` | user |
| `admin` | `admin123` | admin |

### Domain highlights

- Tasks: title, description, status, **priority**, optional **due_date**, owner_id
- List: **pagination** (`page`, `page_size`) + **status** filter; response envelope
- **Admin** lists/reads all tasks; users see own only (authz matrix covered)
- Titles stripped; max lengths enforced; passwords hashed (PBKDF2)

### API surface (summary)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/health` | No | Liveness + env/version |
| POST | `/api/auth/register` | No | Create user + token |
| POST | `/api/auth/login` | No | Token + role |
| GET | `/api/auth/me` | Bearer | Identity + role |
| GET | `/api/tasks` | Bearer | Paginated list (scoped) |
| POST | `/api/tasks` | Bearer | Create |
| GET/PUT/DELETE | `/api/tasks/{id}` | Bearer | Owner or admin |
| POST | `/api/test/reset` | No | **Only when `APP_ENV=test`** |

Docs when running: `http://127.0.0.1:8000/docs`

---

## Prerequisites

- Python **3.12+**
- pip
- Network once for Playwright Chromium

---

## Quick start

```bash
git clone https://github.com/qiaoliang999/qa-automation-web-api-suite.git
cd qa-automation-web-api-suite

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

### Run the app

```bash
# normal local use (reset endpoint disabled)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# test mode (enables /api/test/reset) — used by UI automation
# APP_ENV=test uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Run the suite

API tests set `APP_ENV=test` via conftest; no manual server needed for API/contract.

```bash
# Full suite
pytest

# By layer
pytest -m "api or contract"
pytest -m ui
pytest -m smoke

# Reports
mkdir -p artifacts
pytest -m "api or contract" \
  --junitxml=artifacts/junit-api.xml \
  --html=artifacts/report-api.html --self-contained-html
```

UI failures: screenshots under `artifacts/screenshots/`, traces under `artifacts/traces/`.

---

## Suite map

| Marker | Focus |
| --- | --- |
| `contract` | OpenAPI validity + response schema checks |
| `api` | Auth, CRUD, validation matrices, pagination, reset gate |
| `authz` | Role/ownership matrix (parametrized) |
| `ui` | Login, CRUD in browser, admin list, hybrid API-seed |
| `smoke` | PR-sized gate |
| `regression` | Lifecycle happy path |

See [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md) for layer rationale.

---

## CI

Jobs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

1. **lint** — `ruff check app tests`
2. **api-contract** — `pytest -m "api or contract"` + JUnit/HTML
3. **ui** — Playwright Chromium + UI markers (depends on api-contract)
4. **smoke** — `pytest -m smoke` as a compact gate

Artifacts uploaded per job (`artifacts/`).

---

## Documentation

- [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md) — pyramid, isolation, auth bootstrap
- [`test-cases/functional-test-cases.md`](test-cases/functional-test-cases.md)
- [`reports/DEF-001-whitespace-title-validation.md`](reports/DEF-001-whitespace-title-validation.md) — fixed validation regression
- [`reports/DEF-002-demo-token-security.md`](reports/DEF-002-demo-token-security.md) — residual auth design risk

---

## Design choices and residual limitations

| Choice | Trade-off |
| --- | --- |
| SQLite | Simple, file-based isolation; not multi-host concurrent SUT |
| PBKDF2 (stdlib) | No bcrypt binary dependency; iterations lowered in tests |
| Opaque session tokens | Not JWTs; no token expiry policy beyond process/store |
| TestClient for API | Fast/reliable; slightly different stack path than pure network clients |
| Chromium-only CI | Lean pipeline; Firefox/WebKit not run by default |
| Single UI server process | Fine for this suite; not a load test |

These are intentional so the focus stays on **automation quality** with a credible multi-role SUT.

---

## License

MIT — see [LICENSE](LICENSE).
