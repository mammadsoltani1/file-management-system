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


def test_deleted_file_excluded_from_listing_but_appears_in_trash(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers)

    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert listing["files"] == []

    trash = client.get("/api/v1/trash", headers=auth_headers).json()
    assert [f["id"] for f in trash["files"]] == [uploaded["id"]]


def test_restore_file_reappears_in_listing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers)
    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    trash = client.get("/api/v1/trash", headers=auth_headers).json()
    batch_id = trash["files"][0]["trash_batch_id"]

    response = client.post(f"/api/v1/trash/{batch_id}/restore", headers=auth_headers)
    assert response.status_code == 204

    listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert [f["name"] for f in listing["files"]] == ["a.txt"]

    trash_after = client.get("/api/v1/trash", headers=auth_headers).json()
    assert trash_after["files"] == []


def test_recursive_folder_delete_restore_preserves_hierarchy(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    root = _create_folder(client, auth_headers, name="Root")
    sub = _create_folder(client, auth_headers, name="Sub", parent_id=root["id"])
    file_in_sub = _upload(client, auth_headers, filename="s.txt", folder_id=sub["id"])

    delete_response = client.delete(
        f"/api/v1/folders/{root['id']}?recursive=true", headers=auth_headers
    )
    assert delete_response.status_code == 204

    trash = client.get("/api/v1/trash", headers=auth_headers).json()
    batch_ids = {f["trash_batch_id"] for f in trash["folders"]} | {
        f["trash_batch_id"] for f in trash["files"]
    }
    assert len(batch_ids) == 1
    assert len(trash["folders"]) == 2
    assert len(trash["files"]) == 1
    batch_id = batch_ids.pop()

    restore_response = client.post(
        f"/api/v1/trash/{batch_id}/restore", headers=auth_headers
    )
    assert restore_response.status_code == 204

    restored_sub = client.get(
        f"/api/v1/folders?parent_id={root['id']}", headers=auth_headers
    ).json()
    assert [f["name"] for f in restored_sub] == ["Sub"]

    restored_files = client.get(
        f"/api/v1/files?folder_id={sub['id']}", headers=auth_headers
    ).json()
    assert [f["id"] for f in restored_files["files"]] == [file_in_sub["id"]]


def test_purge_permanently_removes_file(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers)
    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)
 
    trash = client.get("/api/v1/trash", headers=auth_headers).json()
    batch_id = trash["files"][0]["trash_batch_id"]

    response = client.delete(f"/api/v1/trash/{batch_id}", headers=auth_headers)
    assert response.status_code == 204

    trash_after = client.get("/api/v1/trash", headers=auth_headers).json()
    assert trash_after["files"] == []

    restore_response = client.post(
        f"/api/v1/trash/{batch_id}/restore", headers=auth_headers
    )
    assert restore_response.status_code == 404


def test_restore_missing_batch(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/api/v1/trash/{uuid.uuid4()}/restore", headers=auth_headers
    )

    assert response.status_code == 404


def test_purge_missing_batch(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete(f"/api/v1/trash/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404


def test_restore_name_conflict(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    original = _upload(client, auth_headers, filename="dup.txt")
    client.delete(f"/api/v1/files/{original['id']}", headers=auth_headers)

    trash = client.get("/api/v1/trash", headers=auth_headers).json()
    batch_id = trash["files"][0]["trash_batch_id"]

    _upload(client, auth_headers, filename="dup.txt")

    response = client.post(f"/api/v1/trash/{batch_id}/restore", headers=auth_headers)
    assert response.status_code == 409


def test_trash_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/trash")

    assert response.status_code == 401


def test_trash_is_isolated_per_user(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    uploaded = _upload(client, auth_headers)
    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    register_user(email="other@example.com")
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "password123"},
    ).json()["access_token"]

    other_trash = client.get(
        "/api/v1/trash", headers={"Authorization": f"Bearer {other_token}"}
    ).json()

    assert other_trash == {"folders": [], "files": []}
