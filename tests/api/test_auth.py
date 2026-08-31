from fastapi.testclient import TestClient


def test_register_returns_public_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_conflicts(client: TestClient, register_user) -> None:
    register_user(email="dup@example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )

    assert response.status_code == 409


def test_register_lowercases_email(client: TestClient, register_user) -> None:
    register_user(email="Mixed@Example.com")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "mixed@example.com", "password": "password123"},
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )

    assert response.status_code == 422


def test_login_with_correct_credentials(client: TestClient, register_user) -> None:
    register_user(email="login@example.com", password="password123")

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password(client: TestClient, register_user) -> None:
    register_user(email="login2@example.com", password="password123")

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login2@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_login_with_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "password123"},
    )

    assert response.status_code == 401
