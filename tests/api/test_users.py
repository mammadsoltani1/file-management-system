from fastapi.testclient import TestClient


def test_get_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_get_me_returns_current_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_get_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401
