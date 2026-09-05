import uuid

from fastapi.testclient import TestClient


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


def _create_folder(client, auth_headers, name="Folder"):
    response = client.post("/api/v1/folders", json={"name": name}, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


# --- bulk delete ---


def test_bulk_delete_files(client: TestClient, auth_headers: dict[str, str]) -> None:
    f1 = _upload(client, auth_headers, filename="a.txt")
    f2 = _upload(client, auth_headers, filename="b.txt")

    response = client.post(
        "/api/v1/files/bulk/delete",
        json={"file_ids": [f1["id"], f2["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 204
    listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert listing["files"] == []


def test_bulk_delete_with_unknown_id_is_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    f1 = _upload(client, auth_headers)

    response = client.post(
        "/api/v1/files/bulk/delete",
        json={"file_ids": [f1["id"], str(uuid.uuid4())]},
        headers=auth_headers,
    )

    assert response.status_code == 404
    # nothing should have been deleted since the whole batch failed
    listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert len(listing["files"]) == 1


def test_bulk_delete_rejects_duplicate_ids(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    f1 = _upload(client, auth_headers)

    response = client.post(
        "/api/v1/files/bulk/delete",
        json={"file_ids": [f1["id"], f1["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_bulk_delete_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/files/bulk/delete", json={"file_ids": [str(uuid.uuid4())]}
    )

    assert response.status_code == 401


# --- bulk move ---


def test_bulk_move_files(client: TestClient, auth_headers: dict[str, str]) -> None:
    f1 = _upload(client, auth_headers, filename="a.txt")
    f2 = _upload(client, auth_headers, filename="b.txt")
    folder = _create_folder(client, auth_headers, name="Dest")

    response = client.post(
        "/api/v1/files/bulk/move",
        json={"file_ids": [f1["id"], f2["id"]], "folder_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 204
    listing = client.get(
        f"/api/v1/files?folder_id={folder['id']}", headers=auth_headers
    ).json()
    assert sorted(f["name"] for f in listing["files"]) == ["a.txt", "b.txt"]


def test_bulk_move_to_missing_folder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    f1 = _upload(client, auth_headers)

    response = client.post(
        "/api/v1/files/bulk/move",
        json={"file_ids": [f1["id"]], "folder_id": str(uuid.uuid4())},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_bulk_move_name_conflict_at_destination(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Dest")
    _upload(client, auth_headers, filename="dup.txt", folder_id=folder["id"])
    mover = _upload(client, auth_headers, filename="dup.txt")

    response = client.post(
        "/api/v1/files/bulk/move",
        json={"file_ids": [mover["id"]], "folder_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_bulk_move_already_in_destination_is_not_a_conflict(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Dest")
    already_there = _upload(
        client, auth_headers, filename="a.txt", folder_id=folder["id"]
    )

    response = client.post(
        "/api/v1/files/bulk/move",
        json={"file_ids": [already_there["id"]], "folder_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 204


# --- bulk copy ---


def test_bulk_copy_files(client: TestClient, auth_headers: dict[str, str]) -> None:
    f1 = _upload(client, auth_headers, filename="a.txt")
    f2 = _upload(client, auth_headers, filename="b.txt")
    folder = _create_folder(client, auth_headers, name="Dest")

    response = client.post(
        "/api/v1/files/bulk/copy",
        json={"file_ids": [f1["id"], f2["id"]], "folder_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 201
    copies = response.json()
    assert len(copies) == 2
    assert {c["id"] for c in copies} != {f1["id"], f2["id"]}
    assert all(c["folder_id"] == folder["id"] for c in copies)

    # originals remain at root
    root_listing = client.get("/api/v1/files", headers=auth_headers).json()
    assert sorted(f["name"] for f in root_listing["files"]) == ["a.txt", "b.txt"]


def test_bulk_copy_into_same_folder_as_existing_file_conflicts(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Dest")
    _upload(client, auth_headers, filename="a.txt", folder_id=folder["id"])
    source = _upload(client, auth_headers, filename="a.txt")

    response = client.post(
        "/api/v1/files/bulk/copy",
        json={"file_ids": [source["id"]], "folder_id": folder["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 409


def test_bulk_copy_with_unknown_id_is_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/files/bulk/copy",
        json={"file_ids": [str(uuid.uuid4())], "folder_id": None},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_bulk_copy_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/files/bulk/copy",
        json={"file_ids": [str(uuid.uuid4())], "folder_id": None},
    )

    assert response.status_code == 401
