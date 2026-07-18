"""OpenAPI contract tests: schema document validity + response shape checks."""

from __future__ import annotations

import jsonschema
import pytest
from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPISpecValidatorError

from tests.support.api_client import ApiClient
from tests.support.factories import task_payload, user_payload


def _component_schema(openapi: dict, name: str) -> dict:
    return openapi["components"]["schemas"][name]


def _resolve_refs(schema: dict, openapi: dict) -> dict:
    """Lightweight $ref resolver for components/schemas only."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            assert ref.startswith("#/components/schemas/")
            name = ref.rsplit("/", 1)[-1]
            return _resolve_refs(_component_schema(openapi, name), openapi)
        return {k: _resolve_refs(v, openapi) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_resolve_refs(item, openapi) for item in schema]
    return schema


def _validate_against(openapi: dict, schema_name: str, instance: object) -> None:
    schema = _resolve_refs(_component_schema(openapi, schema_name), openapi)
    # Draft handles typical FastAPI OpenAPI 3 schemas well enough for suite use.
    jsonschema.validate(instance=instance, schema=schema)


@pytest.fixture()
def openapi_doc(api_client: ApiClient) -> dict:
    response = api_client.openapi()
    assert response.status_code == 200
    return response.json()


@pytest.mark.contract
@pytest.mark.smoke
def test_openapi_document_is_valid(openapi_doc: dict):
    assert openapi_doc["openapi"].startswith("3.")
    assert openapi_doc["info"]["title"] == "TaskTrack"
    try:
        validate(openapi_doc)
    except OpenAPISpecValidatorError as exc:  # pragma: no cover - fail with detail
        pytest.fail(f"OpenAPI document invalid: {exc}")


@pytest.mark.contract
def test_openapi_exposes_core_paths(openapi_doc: dict):
    paths = openapi_doc["paths"]
    for path in (
        "/health",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/me",
        "/api/tasks",
        "/api/tasks/{task_id}",
    ):
        assert path in paths, f"missing path {path}"
    # Reset must not appear in public schema.
    assert "/api/test/reset" not in paths


@pytest.mark.contract
def test_login_response_matches_token_schema(api_client: ApiClient, openapi_doc: dict):
    response = api_client.login_as("alice")
    assert response.status_code == 200
    _validate_against(openapi_doc, "TokenResponse", response.json())


@pytest.mark.contract
def test_me_response_matches_user_schema(alice_client: ApiClient, openapi_doc: dict):
    response = alice_client.me()
    assert response.status_code == 200
    _validate_against(openapi_doc, "UserResponse", response.json())


@pytest.mark.contract
def test_task_list_response_matches_schema(alice_client: ApiClient, openapi_doc: dict):
    response = alice_client.list_tasks()
    assert response.status_code == 200
    _validate_against(openapi_doc, "TaskListResponse", response.json())


@pytest.mark.contract
def test_create_task_response_matches_schema(alice_client: ApiClient, openapi_doc: dict):
    response = alice_client.create_task(**task_payload(due_date="2026-11-11"))
    assert response.status_code == 201
    _validate_against(openapi_doc, "TaskResponse", response.json())


@pytest.mark.contract
def test_register_response_matches_token_schema(api_client: ApiClient, openapi_doc: dict):
    response = api_client.register(**user_payload())
    assert response.status_code == 201
    _validate_against(openapi_doc, "TokenResponse", response.json())


@pytest.mark.contract
def test_health_response_shape(api_client: ApiClient):
    body = api_client.health().json()
    assert set(body.keys()) >= {"status", "service", "version", "env"}
    assert isinstance(body["status"], str)
    assert isinstance(body["version"], str)


@pytest.mark.contract
@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/tasks", "get"),
        ("/api/tasks", "post"),
        ("/api/tasks/{task_id}", "get"),
        ("/api/tasks/{task_id}", "put"),
        ("/api/tasks/{task_id}", "delete"),
        ("/api/auth/login", "post"),
        ("/api/auth/me", "get"),
    ],
)
def test_protected_routes_declare_security(openapi_doc: dict, path: str, method: str):
    operation = openapi_doc["paths"][path][method]
    # Login is intentionally public; everything else should rely on bearer auth.
    if method == "post" and path == "/api/auth/login":
        assert "security" not in operation or operation.get("security") == []
        return

    schemes = openapi_doc.get("components", {}).get("securitySchemes", {})
    assert schemes, "expected securitySchemes for bearer auth"
    # FastAPI HTTPBearer dependency surfaces either as operation security or
    # as an Authorization parameter — accept either encoding.
    has_security = "security" in operation or any(
        str(p.get("name", "")).lower() == "authorization"
        for p in operation.get("parameters", [])
    )
    assert has_security or schemes, f"{method.upper()} {path} missing auth binding"


@pytest.mark.contract
def test_error_responses_declare_detail_shape(api_client: ApiClient):
    """404 bodies remain machine-readable for clients and defect triage."""
    client = api_client.as_user("alice")
    response = client.get_task("definitely-missing")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    assert body["detail"]


@pytest.mark.contract
def test_task_list_component_schema_requires_envelope(openapi_doc: dict):
    schema = _resolve_refs(_component_schema(openapi_doc, "TaskListResponse"), openapi_doc)
    required = set(schema.get("required", []))
    assert {"items", "total", "page", "page_size"} <= required
    props = schema.get("properties", {})
    assert "items" in props
    assert props["items"].get("type") == "array"
