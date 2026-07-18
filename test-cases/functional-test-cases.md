# TaskTrack — Manual Functional Test Cases

These sample test cases document expected behavior for the TaskTrack demo application.
Automated coverage maps to many of these cases under `tests/api` and `tests/ui`.

---

## TC-AUTH-001 — Successful login (seeded user)

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-001 |
| **Title** | User can log in with valid seeded credentials |
| **Type** | Functional / Smoke |
| **Priority** | P0 |
| **Preconditions** | Application is running; seed data loaded |
| **Test data** | username=`alice`, password=`alice123` |

**Steps**
1. Navigate to `/login`.
2. Enter username `alice` and password `alice123`.
3. Click **Login**.

**Expected**
- User is redirected to `/tasks`.
- Greeting shows `Hello, Alice Anderson`.
- Seeded tasks for alice are listed.

**Automation**
- UI: `tests/ui/test_login.py::test_login_success`
- API: `tests/api/test_auth.py::test_login_success`

---

## TC-AUTH-002 — Login rejects invalid password

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-002 |
| **Title** | Login fails with incorrect password |
| **Type** | Functional / Negative |
| **Priority** | P0 |
| **Preconditions** | Application is running |
| **Test data** | username=`alice`, password=`wrong` |

**Steps**
1. Open `/login`.
2. Enter valid username and incorrect password.
3. Submit the form.

**Expected**
- User remains on the login page.
- Error message: `Invalid username or password`.
- No authenticated cookie / token is issued.

**Automation**
- UI: `tests/ui/test_login.py::test_login_failure_shows_error`
- API: `tests/api/test_auth.py::test_login_invalid_password`

---

## TC-AUTH-003 — Register new user

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-003 |
| **Title** | API allows registration of a unique username |
| **Type** | Functional |
| **Priority** | P1 |
| **Preconditions** | Username does not already exist |

**Steps**
1. `POST /api/auth/register` with unique username, password (≥4), display_name.
2. Observe response.
3. Call `GET /api/auth/me` with returned token.

**Expected**
- HTTP 201 with `access_token`.
- `/me` returns the new user's identity.

**Automation**
- API: `tests/api/test_auth.py::test_register_new_user`

---

## TC-AUTH-004 — Unauthorized access is blocked

| Field | Value |
| --- | --- |
| **ID** | TC-AUTH-004 |
| **Title** | Protected endpoints require authentication |
| **Type** | Security / Functional |
| **Priority** | P0 |

**Steps**
1. Call `GET /api/tasks` without Authorization header.
2. Open `/tasks` in a browser without login cookie.

**Expected**
- API returns HTTP 401.
- UI redirects to `/login`.

**Automation**
- API: `tests/api/test_tasks.py::test_list_tasks_unauthorized`
- UI: `tests/ui/test_login.py::test_tasks_page_requires_login`

---

## TC-TASK-001 — Create task (happy path)

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-001 |
| **Title** | Authenticated user can create a task |
| **Type** | Functional / Smoke |
| **Priority** | P0 |
| **Preconditions** | Logged in as alice |

**Steps**
1. Open tasks page (or call `POST /api/tasks`).
2. Provide title, optional description, status.
3. Submit.

**Expected**
- Task appears in the owner's list.
- Status and description match input.
- Other users cannot see the task.

**Automation**
- UI: `tests/ui/test_tasks.py::test_create_task_happy_path`
- API: `tests/api/test_tasks.py::test_create_task`

---

## TC-TASK-002 — Create task without title (negative)

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-002 |
| **Title** | Empty title is rejected |
| **Type** | Functional / Negative / Validation |
| **Priority** | P1 |

**Steps**
1. Submit create-task form with blank/whitespace title.
2. Or call API with empty title.

**Expected**
- Request is rejected (UI shows `Title is required`; API returns 422).
- Task list is unchanged.

**Automation**
- UI: `tests/ui/test_tasks.py::test_create_task_empty_title_negative`
- API: `tests/api/test_tasks.py::test_create_task_empty_title`

---

## TC-TASK-003 — Update task status

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-003 |
| **Title** | Owner can update task status |
| **Type** | Functional |
| **Priority** | P1 |
| **Preconditions** | Seeded task `task-1` exists for alice |

**Steps**
1. Log in as alice.
2. Change status of "Write test plan" to `done`.
3. Confirm list reflects new status.

**Expected**
- Status badge updates to `done`.
- Success confirmation is shown (UI).

**Automation**
- UI: `tests/ui/test_tasks.py::test_update_task_status`
- API: `tests/api/test_tasks.py::test_update_task`

---

## TC-TASK-004 — Delete task

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-004 |
| **Title** | Owner can delete a task |
| **Type** | Functional |
| **Priority** | P1 |

**Steps**
1. Create a temporary task.
2. Delete it via UI or `DELETE /api/tasks/{id}`.
3. Attempt to fetch the same id.

**Expected**
- Task disappears from the list.
- API returns 404 for subsequent GET.

**Automation**
- UI: `tests/ui/test_tasks.py::test_delete_task`
- API: `tests/api/test_tasks.py::test_delete_task`

---

## TC-TASK-005 — Ownership isolation

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-005 |
| **Title** | Users cannot access another user's tasks |
| **Type** | Security / Functional |
| **Priority** | P0 |

**Steps**
1. Log in as alice.
2. Attempt to GET/PUT/DELETE bob's `task-3`.

**Expected**
- API returns HTTP 403 Forbidden.
- UI list for alice never includes bob's tasks.

**Automation**
- API: `test_get_other_users_task_forbidden`, `test_update_other_users_task_forbidden`, `test_delete_other_users_task_forbidden`
- UI: `tests/ui/test_tasks.py::test_seeded_tasks_visible_after_login`

---

## TC-TASK-006 — Full CRUD lifecycle

| Field | Value |
| --- | --- |
| **ID** | TC-TASK-006 |
| **Title** | Create → Read → Update → Delete lifecycle |
| **Type** | Regression |
| **Priority** | P0 |

**Steps**
1. Create a task via API.
2. Read it by id.
3. Update description/status.
4. Delete it.
5. Confirm 404 on subsequent GET.

**Expected**
- Each step succeeds with correct status codes and payload.

**Automation**
- API: `tests/api/test_tasks.py::test_full_crud_lifecycle`
