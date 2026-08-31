import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient


def _upload(
    client, auth_headers, filename="hello.txt", content=b"hello world", **extra
):
    files = {"upload": (filename, content, "text/plain")}
    return client.post(
        "/api/v1/files/upload", files=files, data=extra, headers=auth_headers
    )


def test_upload_file(client: TestClient, auth_headers: dict[str, str]) -> None:
    content = b"hello world"

    response = _upload(client, auth_headers, content=content)

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "hello.txt"
    assert body["size_bytes"] == len(content)
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert body["content_type"] == "text/plain"
    assert body["folder_id"] is None


def test_upload_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/files/upload", files={"upload": ("a.txt", b"hi", "text/plain")}
    )

    assert response.status_code == 401


def test_upload_into_missing_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = _upload(client, auth_headers, folder_id=str(uuid.uuid4()))

    assert response.status_code == 404


def test_upload_into_owned_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = client.post(
        "/api/v1/folders", json={"name": "Docs"}, headers=auth_headers
    ).json()

    response = _upload(client, auth_headers, folder_id=folder["id"])

    assert response.status_code == 201
    assert response.json()["folder_id"] == folder["id"]


def test_upload_too_large_is_rejected(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 5)

    response = _upload(client, auth_headers, content=b"this is way too big")

    assert response.status_code == 413


def test_upload_sanitizes_path_traversal_in_filename(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = _upload(client, auth_headers, filename="../../etc/passwd")

    assert response.status_code == 201
    assert response.json()["original_filename"] == "passwd"


def test_list_directory_returns_folders_and_files(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/api/v1/folders", json={"name": "Photos"}, headers=auth_headers)
    _upload(client, auth_headers, filename="a.txt")

    response = client.get("/api/v1/files", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert [f["name"] for f in body["folders"]] == ["Photos"]
    assert [f["original_filename"] for f in body["files"]] == ["a.txt"]


def test_download_file(client: TestClient, auth_headers: dict[str, str]) -> None:
    content = b"download me"
    uploaded = _upload(client, auth_headers, content=content).json()

    response = client.get(
        f"/api/v1/files/{uploaded['id']}/download", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.content == content
    assert "hello.txt" in response.headers["content-disposition"]


def test_download_missing_file(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        f"/api/v1/files/{uuid.uuid4()}/download", headers=auth_headers
    )

    assert response.status_code == 404


def test_download_another_users_file_is_not_found(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    uploaded = _upload(client, auth_headers).json()

    register_user(email="other@example.com")
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.get(
        f"/api/v1/files/{uploaded['id']}/download",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404


def test_delete_file(client: TestClient, auth_headers: dict[str, str]) -> None:
    uploaded = _upload(client, auth_headers).json()

    response = client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)
    assert response.status_code == 204

    listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert listing["files"] == []


def test_delete_file_twice_is_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers).json()

    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)
    response = client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    assert response.status_code == 404


def test_delete_missing_file(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete(f"/api/v1/files/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404
