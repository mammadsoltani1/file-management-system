
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


def test_search_finds_matching_folders_and_files_case_insensitively(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Reports")
    _create_folder(client, auth_headers, name="report_archive")
    _upload(client, auth_headers, filename="Report_final.txt", folder_id=folder["id"])
    _upload(client, auth_headers, filename="unrelated.txt")

    response = client.get(
        "/api/v1/search", params={"query": " REPORT "}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "REPORT"
    names = [item["name"] for item in body["items"]]
    assert names == ["report_archive", "Report_final.txt", "Reports"]


def test_search_file_result_has_folder_id_as_parent(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    folder = _create_folder(client, auth_headers, name="Docs")
    _upload(client, auth_headers, filename="unique_name.txt", folder_id=folder["id"])

    response = client.get(
        "/api/v1/search", params={"query": "unique_name"}, headers=auth_headers
    )

    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["item_type"] == "file"
    assert body["items"][0]["parent_id"] == folder["id"]


def test_search_escapes_like_wildcards(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _upload(client, auth_headers, filename="normal.txt")

    response = client.get("/api/v1/search", params={"query": "%"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["total_items"] == 0


def test_search_rejects_whitespace_only_query(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/search", params={"query": "   "}, headers=auth_headers
    )

    assert response.status_code == 422


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"query": "anything"})

    assert response.status_code == 401


def test_search_is_isolated_per_user(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    _upload(client, auth_headers, filename="mine.txt")

    register_user(email="other@example.com")
    other_token = client.post(
        "/api/v1/auth/login",
        data={"username": "other@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.get(
        "/api/v1/search",
        params={"query": "mine"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.json()["items"] == []


def test_search_paginates_results(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for i in range(3):
        _upload(client, auth_headers, filename=f"page-item-{i}.txt")

    response = client.get(
        "/api/v1/search",
        params={"query": "page-item", "page": 1, "page_size": 2},
        headers=auth_headers,
    )

    body = response.json()
    assert len(body["items"]) == 2
    assert body["total_items"] == 3
    assert body["total_pages"] == 2


def test_search_does_not_return_trashed_items(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers, filename="trashme.txt")
    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    response = client.get(
        "/api/v1/search", params={"query": "trashme"}, headers=auth_headers
    )

    assert response.json()["items"] == []
