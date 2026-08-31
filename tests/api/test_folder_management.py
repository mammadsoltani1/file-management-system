import uuid

from fastapi.testclient import TestClient


def _create_folder(client, auth_headers, name="Folder", parent_id=None):
    payload = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    response = client.post("/api/v1/folders", json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _upload(client, auth_headers, filename="a.txt", folder_id=None):
    data = {"folder_id": folder_id} if folder_id is not None else {}
    response = client.post(
        "/api/v1/files/upload",
        files={"upload": (filename, b"content", "text/plain")},
        data=data,
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_delete_empty_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    folder = _create_folder(client, auth_headers, name="Empty")

    response = client.delete(f"/api/v1/folders/{folder['id']}", headers=auth_headers)

    assert response.status_code == 204
    listing = client.get("/api/v1/folders", headers=auth_headers).json()
    assert listing == []


def test_delete_missing_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/api/v1/folders/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404


def test_delete_non_empty_folder_without_recursive_conflicts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Docs")
    _upload(client, auth_headers, folder_id=folder["id"])

    response = client.delete(f"/api/v1/folders/{folder['id']}", headers=auth_headers)

    assert response.status_code == 409


def test_delete_recursive_removes_nested_folders_and_files(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    root = _create_folder(client, auth_headers, name="Root")
    sub = _create_folder(client, auth_headers, name="Sub", parent_id=root["id"])
    _upload(client, auth_headers, filename="root.txt", folder_id=root["id"])
    sub_file = _upload(client, auth_headers, filename="sub.txt", folder_id=sub["id"])

    response = client.delete(
        f"/api/v1/folders/{root['id']}?recursive=true", headers=auth_headers
    )
    assert response.status_code == 204

    folders_listing = client.get("/api/v1/folders", headers=auth_headers).json()
    assert folders_listing == []

    download = client.get(
        f"/api/v1/files/{sub_file['id']}/download", headers=auth_headers
    )
    assert download.status_code == 404


def test_delete_folder_requires_owner(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    folder = _create_folder(client, auth_headers, name="Mine")

    register_user(email="other@example.com")
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.delete(
        f"/api/v1/folders/{folder['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_rename_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    folder = _create_folder(client, auth_headers, name="Old")

    response = client.patch(
        f"/api/v1/folders/{folder['id']}/rename",
        json={"name": "New"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_rename_missing_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"/api/v1/folders/{uuid.uuid4()}/rename",
        json={"name": "New"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_rename_to_duplicate_name_conflicts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_folder(client, auth_headers, name="Taken")
    folder = _create_folder(client, auth_headers, name="Movable")

    response = client.patch(
        f"/api/v1/folders/{folder['id']}/rename",
        json={"name": "Taken"},
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_rename_to_invalid_name_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Ok")

    response = client.patch(
        f"/api/v1/folders/{folder['id']}/rename",
        json={"name": ".."},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_move_folder_into_nested_destination(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    a = _create_folder(client, auth_headers, name="A")
    b = _create_folder(client, auth_headers, name="B", parent_id=a["id"])
    c = _create_folder(client, auth_headers, name="C", parent_id=b["id"])
    x = _create_folder(client, auth_headers, name="X")

    response = client.patch(
        f"/api/v1/folders/{x['id']}/move",
        json={"parent_id": c["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["parent_id"] == c["id"]


def test_move_folder_to_root(client: TestClient, auth_headers: dict[str, str]) -> None:
    parent = _create_folder(client, auth_headers, name="Parent")
    child = _create_folder(client, auth_headers, name="Child", parent_id=parent["id"])

    response = client.patch(
        f"/api/v1/folders/{child['id']}/move",
        json={"parent_id": None},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["parent_id"] is None


def test_move_folder_into_itself_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Self")

    response = client.patch(
        f"/api/v1/folders/{folder['id']}/move",
        json={"parent_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_move_folder_into_own_descendant_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    parent = _create_folder(client, auth_headers, name="Parent")
    child = _create_folder(client, auth_headers, name="Child", parent_id=parent["id"])

    response = client.patch(
        f"/api/v1/folders/{parent['id']}/move",
        json={"parent_id": child["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_move_folder_missing_destination(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Solo")

    response = client.patch(
        f"/api/v1/folders/{folder['id']}/move",
        json={"parent_id": str(uuid.uuid4())},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_move_folder_duplicate_name_at_destination_conflicts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    destination = _create_folder(client, auth_headers, name="Destination")
    _create_folder(client, auth_headers, name="Clash", parent_id=destination["id"])
    mover = _create_folder(client, auth_headers, name="Clash")

    response = client.patch(
        f"/api/v1/folders/{mover['id']}/move",
        json={"parent_id": destination["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_move_missing_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        f"/api/v1/folders/{uuid.uuid4()}/move",
        json={"parent_id": None},
        headers=auth_headers,
    )

    assert response.status_code == 404
