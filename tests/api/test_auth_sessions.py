import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def _allow_cookies_over_http(monkeypatch: pytest.MonkeyPatch) -> None:
    # TestClient talks to "http://testserver"; a Secure cookie would never be
    # attached to a plain-http request, so relax it just for these tests.
    monkeypatch.setattr(settings, "REFRESH_TOKEN_COOKIE_SECURE", False)


def _login(client: TestClient, email: str = "test@example.com") -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_login_sets_refresh_cookie(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies
    assert response.json()["access_token"]


def test_refresh_issues_new_access_token(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_rotates_the_cookie(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)
    first_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    client.post("/api/v1/auth/refresh")

    second_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    assert second_cookie != first_cookie


def test_refresh_without_cookie_is_unauthorized(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_reusing_rotated_refresh_token_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)
    old_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    first_refresh = client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200

    client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, old_cookie)
    reuse_response = client.post("/api/v1/auth/refresh")

    assert reuse_response.status_code == 401


def test_reuse_detection_revokes_the_whole_family(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)
    old_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    client.post("/api/v1/auth/refresh")
    successor_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    # reusing the old, already-rotated token signals theft
    client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, old_cookie)
    client.post("/api/v1/auth/refresh")

    # the legitimate successor should now be revoked too
    client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, successor_cookie)
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_logout_revokes_the_session(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401


def test_logout_without_a_session_still_succeeds(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204


def test_logout_all_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout-all")

    assert response.status_code == 401


def test_logout_all_revokes_every_session_for_the_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _login(client)
    first_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    _login(client)
    second_cookie = client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)

    response = client.post("/api/v1/auth/logout-all", headers=auth_headers)
    assert response.status_code == 204

    client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, first_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401

    client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, second_cookie)
    assert client.post("/api/v1/auth/refresh").status_code == 401
