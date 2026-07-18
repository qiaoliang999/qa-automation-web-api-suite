# DEF-001 — Fixed regression: whitespace-only titles must be rejected

| Field | Value |
| --- | --- |
| **ID** | DEF-001 |
| **Title** | Whitespace-only task titles rejected after strip (API + UI) |
| **Severity** | Medium (data quality / validation) |
| **Priority** | P1 |
| **Status** | **Fixed** — locked by automated regression tests |
| **Environment** | TaskTrack 2.0.0, Windows/Linux, Python 3.12 |
| **Component** | API + UI Tasks |
| **Date found** | 2026-07-18 |
| **Date fixed** | 2026-07-18 |

### Summary

Earlier TaskTrack builds risked inconsistent title handling: Pydantic `min_length` could accept strings that became empty after `.strip()`, or strip logic could diverge between HTML form handlers and JSON API. Empty or whitespace-only titles must never become tasks.

### Root cause

Validation applied length checks before normalization (strip), or strip was only applied in one path.

### Fix

- Pydantic `field_validator` strips `title` / `description` on create and update.
- API handlers re-check empty title after validation and return **422**.
- UI form handler strips title and returns **400** with `Title is required`.
- Max length enforced (title ≤ 120).

### Regression locks

- `tests/api/test_tasks.py::test_create_task_title_validation` (parametrized: whitespace, empty, too-long, strip-ok)
- `tests/api/test_tasks.py::test_update_task_empty_title`
- `tests/ui/test_tasks.py::test_create_task_empty_title_negative`

### Verification

```bash
pytest -k "title_validation or empty_title" -q
```
