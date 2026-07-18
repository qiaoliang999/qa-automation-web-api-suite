# TaskTrack — Manual Functional Test Cases

Sample cases for the TaskTrack demo application (v2). Many map to automated coverage under `tests/api`, `tests/contract`, and `tests/ui`.

---

## TC-AUTH-001 — Successful login (seeded user)

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-001 |
| **Type** | Functional / Smoke |
| **Priority** | P0 |
| **Test data** | `alice / alice123` |

**Steps**
1. Navigate to `/login`.
2. Enter username and password.
3. Submit.

**Expected**
- Redirect to `/tasks`.
- Greeting shows display name.
- Role badge shows `user`.

**Automation**
- UI: `tests/ui/test_login.py::test_login_success`
- API: `tests/api/test_auth.py::test_login_success`

---

## TC-AUTH-002 — Login rejects invalid password

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-002 |
| **Type** | Negative |
| **Priority** | P0 |

**Expected**
- Stay on login; error `Invalid username or password`.
- No session cookie issued.

**Automation**
- UI: `test_login_failure_shows_error`
- API: `test_login_rejects_bad_credentials` (parametrized)

---

## TC-AUTH-003 — Register new user

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-003 |
| **Type** | Functional |
| **Priority** | P1 |

**Expected**
- `POST /api/auth/register` → 201 + token + `role=user`.
- Duplicate username → 409.
- Short username / password → 422.

**Automation**
- `test_register_new_user`, `test_register_duplicate_username`, `test_register_validation_errors`

---

## TC-AUTH-004 — Admin login

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-004 |
| **Test data** | `admin / admin123` |

**Expected**
- Token response `role=admin`.
- UI heading **All Tasks** and role indicator.

**Automation**
- API parametrized login; UI `test_admin_login_shows_role`

---

## TC-TASK-001 — List tasks is ownership-scoped

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-001 |
| **Priority** | P0 |

**Expected**
- User sees only own tasks (paginated envelope: `items`, `total`, `page`, `page_size`).
- Admin sees all tasks.

**Automation**
- `test_list_tasks_returns_owned_only`, `test_admin_lists_all_tasks`, authz matrix

---

## TC-TASK-002 — Create / update / delete task

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-002 |
| **Priority** | P0 |

**Expected**
- Create with title, description, status, priority, optional due_date.
- Title is stripped; whitespace-only title rejected.
- Owner (or admin) can update/delete; peer cannot (403).

**Automation**
- CRUD + `test_task_authz_matrix` + UI happy paths with cookie auth

---

## TC-TASK-003 — Pagination and status filter

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-003 |
| **Priority** | P1 |

**Steps**
1. Authenticate as alice.
2. Create several tasks.
3. `GET /api/tasks?page=1&page_size=3`.
4. `GET /api/tasks?status=todo`.

**Expected**
- Pages are disjoint; totals correct.
- Status filter returns only matching items.
- Invalid status / page bounds → 422.

**Automation**
- `test_list_tasks_pagination`, `test_list_tasks_status_filter`, bounds parametrization

---

## TC-SEC-001 — Test reset not available outside test env

| Field | Value |
| --- | --- |
| **ID** | TC-SEC-001 |
| **Priority** | P0 |

**Expected**
- When `APP_ENV=test`, `POST /api/test/reset` → 200.
- When `APP_ENV=production`, same path → 404.
- Endpoint absent from OpenAPI paths.

**Automation**
- `tests/api/test_reset_gate.py`, contract path list

---

## TC-CONTRACT-001 — OpenAPI document and response shapes

| Field | Value |
| --- | --- |
| **ID** | TC-CONTRACT-001 |
| **Priority** | P1 |

**Expected**
- `/openapi.json` validates with openapi-spec-validator.
- Login/me/task list/create responses match component schemas.

**Automation**
- `tests/contract/test_openapi.py`
