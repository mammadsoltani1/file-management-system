import uuid

from fastapi.testclient import TestClient


def test_create_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/folders", json={"name": "Photos"}, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Photos"
    assert body["parent_id"] is None


def test_list_folders_returns_created_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/api/v1/folders", json={"name": "Photos"}, headers=auth_headers)

    response = client.get("/api/v1/folders", headers=auth_headers)

    assert response.status_code == 200
    names = [f["name"] for f in response.json()]
    assert names == ["Photos"]


def test_create_duplicate_folder_conflicts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/api/v1/folders", json={"name": "Photos"}, headers=auth_headers)

    response = client.post(
        "/api/v1/folders", json={"name": "Photos"}, headers=auth_headers
    )

    assert response.status_code == 409


def test_create_folder_with_missing_parent(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/folders",
        json={"name": "Sub", "parent_id": str(uuid.uuid4())},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_subfolder_and_list_under_parent(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    parent = client.post(
        "/api/v1/folders", json={"name": "Projects"}, headers=auth_headers
    ).json()

    client.post(
        "/api/v1/folders",
        json={"name": "Backend", "parent_id": parent["id"]},
        headers=auth_headers,
    )

    root_listing = client.get("/api/v1/folders", headers=auth_headers).json()
    assert [f["name"] for f in root_listing] == ["Projects"]

    nested_listing = client.get(
        f"/api/v1/folders?parent_id={parent['id']}", headers=auth_headers
    ).json()
    assert [f["name"] for f in nested_listing] == ["Backend"]


def test_create_folder_rejects_invalid_name(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/folders", json={"name": ".."}, headers=auth_headers)

    assert response.status_code == 422


def test_create_folder_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/folders", json={"name": "Photos"})

    assert response.status_code == 401


def test_folders_are_isolated_per_user(client: TestClient, register_user) -> None:
    register_user(email="owner-a@example.com")
    token_a = client.post(
        "/api/v1/auth/login",
        data={"username": "owner-a@example.com", "password": "password123"},
    ).json()["access_token"]

    register_user(email="owner-b@example.com")
    token_b = client.post(
        "/api/v1/auth/login",
        data={"username": "owner-b@example.com", "password": "password123"},
    ).json()["access_token"]

    client.post(
        "/api/v1/folders",
        json={"name": "OwnerAFolder"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    listing_b = client.get(
        "/api/v1/folders", headers={"Authorization": f"Bearer {token_b}"}
    ).json()

    assert listing_b == []
