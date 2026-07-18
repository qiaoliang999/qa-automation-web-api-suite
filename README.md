# QA Automation Web + API Suite

**Portfolio project for QA Automation / Software Test Engineer roles**

Repository: self-contained **system under test** (TaskTrack) + professional **automated test suite** (API + UI), with fixtures, page objects, markers, sample test cases, defect reports, and CI.

---

## Why this project exists

This repository demonstrates practical QA automation skills that map directly to day-to-day work on product teams:

- Designing and testing against a real HTTP API and HTML UI
- Structuring a maintainable pytest suite (fixtures, markers, isolation)
- Page Object Model for UI automation with Playwright
- API client abstraction for httpx-based contract and regression tests
- Failure evidence (screenshots on UI failures)
- Readable manual test cases and defect reports
- CI-ready GitHub Actions pipeline

It is intentionally small and runnable — quality over feature sprawl.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| SUT (app) | Python 3.12, FastAPI, Jinja2 templates, in-memory store |
| API tests | pytest + httpx |
| UI tests | pytest + Playwright (Chromium) |
| Reporting | pytest-html, screenshot artifacts on UI failure |
| CI | GitHub Actions (install deps, Playwright browsers, run suite) |

---

## Architecture

```
qa-automation-web-api-suite/
├── app/                      # TaskTrack demo application (system under test)
│   ├── main.py               # FastAPI routes: auth, tasks CRUD, HTML UI
│   ├── models.py             # Pydantic models
│   ├── database.py           # In-memory store + seed data
│   ├── templates/            # Login + tasks pages
│   └── static/               # Minimal CSS
├── tests/
│   ├── conftest.py           # Server lifecycle, fixtures, screenshot hook
│   ├── helpers/              # Config + ApiClient
│   ├── api/                  # Auth + task API tests
│   └── ui/                   # Playwright tests + page objects
├── test-cases/               # Manual functional test cases (Markdown)
├── reports/                  # Defect template + example defect reports
├── .github/workflows/ci.yml  # CI pipeline
├── pytest.ini
├── requirements.txt
└── README.md
```

**Test isolation:** every test receives a reset data store via `POST /api/test/reset` (fixture-driven). Seeded users/tasks are reloaded so order does not matter.

**UI automation:** page objects under `tests/ui/pages/` encapsulate selectors (`data-testid`) and actions. A pytest hook captures a full-page screenshot under `artifacts/screenshots/` when a UI test fails.

---

## Product under test: TaskTrack

A tiny personal task manager.

### Seeded accounts

| Username | Password | Display name |
| --- | --- | --- |
| `alice` | `alice123` | Alice Anderson |
| `bob` | `bob1234` | Bob Baker |

### API surface (summary)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/health` | No | Liveness |
| POST | `/api/auth/register` | No | Create user + token |
| POST | `/api/auth/login` | No | Username/password → token |
| GET | `/api/auth/me` | Bearer | Current user |
| GET/POST | `/api/tasks` | Bearer | List / create owned tasks |
| GET/PUT/DELETE | `/api/tasks/{id}` | Bearer | Read / update / delete (owner only) |
| GET/POST | `/login`, `/tasks`, … | Cookie | HTML UI flows |

Interactive docs when the app is running: `http://127.0.0.1:8000/docs`

---

## Prerequisites

- Python **3.12+**
- pip
- Network access once to install Playwright browser binaries

No Docker required.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/qiaoliang999/qa-automation-web-api-suite.git
cd qa-automation-web-api-suite

# 2. (Recommended) virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Install Chromium for Playwright
python -m playwright install chromium
```

### Run the application only

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login and sign in with `alice` / `alice123`.

### Run the automated suite

The session-scoped fixture starts Uvicorn automatically if nothing is already listening on port 8000.

```bash
# Full suite
pytest

# Smoke only (fast PR-style gate)
pytest -m smoke

# API only
pytest -m api

# UI only
pytest -m ui

# HTML report
pytest --html=artifacts/report.html --self-contained-html
```

On UI failure, screenshots are written to `artifacts/screenshots/`.

---

## What the suite covers

### API (`@pytest.mark.api`)

- Health check
- Login success / invalid credentials / unknown user
- Register + duplicate username + validation errors
- `/me` with and without token
- Task list ownership isolation
- Create / read / update / delete
- Empty title and invalid status validation
- Unauthorized and forbidden (cross-user) access
- Full CRUD lifecycle regression

### UI (`@pytest.mark.ui`)

- Login success and failure messaging
- Logout
- Tasks page requires authentication
- Create task happy path
- Create task empty-title negative path
- Update status and delete task
- Seeded data visibility / isolation in the browser

Markers are defined in `pytest.ini` (`api`, `ui`, `smoke`).

---

## Documentation included

- [`test-cases/functional-test-cases.md`](test-cases/functional-test-cases.md) — sample manual cases mapped to automation
- [`reports/defect-report-template.md`](reports/defect-report-template.md) — reusable defect template
- [`reports/DEF-001-whitespace-title-validation.md`](reports/DEF-001-whitespace-title-validation.md) — example minor UX/validation defect
- [`reports/DEF-002-demo-token-security.md`](reports/DEF-002-demo-token-security.md) — documented intentional security limitation of the demo app

---

## CI

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. Checkout + set up Python 3.12
2. Install requirements
3. Install Playwright Chromium (+ OS deps)
4. Run smoke tests, then full suite
5. Upload `artifacts/` (HTML report / screenshots) on completion

---

## Design choices (and limitations)

| Choice | Rationale / limitation |
| --- | --- |
| In-memory DB | Fast, no external services; data lost on process restart |
| Plain-text demo passwords | Deterministic tests; **not** production auth |
| `/api/test/reset` | Test isolation helper; must not ship on real systems |
| Single-process server | Sufficient for local + CI; not load-test oriented |
| Chromium only in CI | Keeps pipeline lean; Firefox/WebKit easy to add |

These limitations are deliberate so the focus stays on **automation engineering quality**.

---

## Skills demonstrated for QA Automation roles

- Building stable selectors (`data-testid`) and Page Objects
- Fixture-based setup/teardown and test data reset
- API-first coverage plus UI smoke/regression
- Negative testing and authorization checks
- Markers for smoke vs full regression
- CI integration and artifact collection
- Clear communication via test cases and defect reports

---

## License

MIT — see [LICENSE](LICENSE).
