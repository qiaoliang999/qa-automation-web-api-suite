# DEF-001 — Whitespace-only task title accepted by HTML form before server-side validation

| Field | Value |
| --- | --- |
| **ID** | DEF-001 |
| **Title** | Create-task form allows submitting whitespace-only titles (client does not block empty title) |
| **Severity** | Minor |
| **Priority** | P2 |
| **Status** | Closed — documented behavior with server-side guard |
| **Environment** | Windows 10, Chromium (Playwright), TaskTrack 1.0.0 |
| **Build / Commit** | initial portfolio release |
| **Component** | UI / Tasks |
| **Found by** | Automated (`tests/ui/test_tasks.py::test_create_task_empty_title_negative`) + exploratory |
| **Date found** | 2026-07-18 |
| **Assignee** | Demo team |

### Summary
The create-task form HTML input does not set the `required` attribute, so the browser will submit a blank or whitespace-only title. The server correctly rejects the request and re-renders the page with `Title is required`, but the lack of client-side validation produces an unnecessary round-trip and is inconsistent with the login form (which uses `required`).

### Steps to Reproduce
1. Start TaskTrack and log in as `alice / alice123`.
2. On the tasks page, leave **Title** empty (or enter only spaces).
3. Optionally fill Description.
4. Click **Create task**.

### Expected Result
- Prefer: browser-native validation prevents submit when title is empty.
- Minimum: server rejects the request and no new task is created (current behavior).

### Actual Result
- Form submits to the server.
- Server responds with HTTP 400 and alert: `Title is required`.
- Task list remains unchanged (no data corruption).
- No client-side prevention before network call.

### Evidence
- Automated assertion confirms the server-side error message is shown:
  - `tests/ui/test_tasks.py::test_create_task_empty_title_negative`
- API counterpart also enforces non-empty titles:
  - `tests/api/test_tasks.py::test_create_task_empty_title` → HTTP 422

### Impact
- Low functional risk (server protects data integrity).
- Mild UX inconsistency and unnecessary error path.

### Suggested Fix / Notes
Add `required` on the title input and/or trim + validate in a small client script before submit. Keep server-side validation as the source of truth.

### Verification
1. Re-run `pytest tests/ui/test_tasks.py::test_create_task_empty_title_negative -m ui`.
2. Manually confirm empty title cannot create a task.
3. Confirm non-empty titles still create tasks successfully.
