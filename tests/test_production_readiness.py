from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
from pydantic import ValidationError

from core.config.config import Settings, settings
from core.cookies.cookies import set_auth_cookies
from main import API_PREFIX, app


client = TestClient(app)


def test_health_endpoint_is_available_without_external_services() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_paths_are_prefixed_once() -> None:
    response = client.get(f"{API_PREFIX}/openapi.json")

    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert f"{API_PREFIX}/auth/login" in paths
    assert f"{API_PREFIX}/admin/metrics" in paths
    assert f"{API_PREFIX}/catalogues/areas-tematicas" in paths
    assert f"{API_PREFIX}/projects" in paths
    assert not any(path.startswith(f"{API_PREFIX}{API_PREFIX}") for path in paths)


def test_app_has_no_root_path_and_exposes_single_prefix() -> None:
    assert app.root_path == ""
    assert client.post("/auth/login").status_code == 404
    assert client.get(f"{API_PREFIX}/auth/login").status_code != 404


def test_custom_docs_keeps_existing_url_and_points_to_prefixed_openapi() -> None:
    response = client.get(f"{API_PREFIX}/docs")

    assert response.status_code == 200
    assert f"{API_PREFIX}/openapi.json" in response.text


def test_cors_development_default_allows_localhost_with_credentials() -> None:
    response = client.options(
        f"{API_PREFIX}/auth/login",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_origins_are_empty_in_production_and_parsed_from_csv(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CORS_ALLOWED_ORIGINS", "")
    assert settings.cors_allowed_origins == []

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert settings.cors_allowed_origins == ["http://localhost:4200"]

    monkeypatch.setattr(settings, "CORS_ALLOWED_ORIGINS", "https://a.example, https://b.example")
    assert settings.cors_allowed_origins == ["https://a.example", "https://b.example"]


def test_settings_reject_wildcard_cors_origin() -> None:
    try:
        Settings(
            DB_HOST="localhost",
            DB_USER="postgres",
            DB_PASSWORD="postgres",
            DB_NAME="prisma",
            SECRET_KEY="test-secret",
            GOOGLE_CLIENT_ID="test-google-client",
            GOOGLE_CLIENT_SECRET="test-google-secret",
            CORS_ALLOWED_ORIGINS="*",
        )
    except ValidationError:
        return

    raise AssertionError("Settings accepted a wildcard CORS origin with credentials enabled")


def _auth_cookie_headers(monkeypatch, environment: str) -> list[str]:
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    response = JSONResponse({"ok": True})
    set_auth_cookies(response, "access-token", "refresh-token")
    return response.headers.getlist("set-cookie")


def test_cookies_are_not_secure_outside_production(monkeypatch) -> None:
    headers = _auth_cookie_headers(monkeypatch, "development")

    assert len(headers) == 2
    assert all("HttpOnly" in header for header in headers)
    assert all("SameSite=lax" in header for header in headers)
    assert all("Secure" not in header for header in headers)


def test_cookies_are_secure_in_production(monkeypatch) -> None:
    headers = _auth_cookie_headers(monkeypatch, "production")

    assert len(headers) == 2
    assert all("Secure" in header for header in headers)
