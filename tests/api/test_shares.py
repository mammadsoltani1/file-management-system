import uuid

from fastapi.testclient import TestClient

OWNER_EMAIL = "test@example.com"
OWNER_PASSWORD = "password123"
RECIPIENT_EMAIL = "recipient@example.com"
RECIPIENT_PASSWORD = "password123"


def _upload(client, auth_headers, filename="a.txt"):
    response = client.post(
        "/api/v1/files/upload",
        files={"upload": (filename, b"shared content", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _recipient_headers(client: TestClient, register_user) -> dict[str, str]:
    register_user(email=RECIPIENT_EMAIL, password=RECIPIENT_PASSWORD)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": RECIPIENT_EMAIL, "password": RECIPIENT_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _share(client, auth_headers, file_id, recipient_email=RECIPIENT_EMAIL):
    return client.post(
        f"/api/v1/shares/files/{file_id}",
        json={"recipient_email": recipient_email},
        headers=auth_headers,
    )


def test_share_file_returns_recipient_details(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)

    response = _share(client, auth_headers, uploaded["id"])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["file_id"] == uploaded["id"]
    assert body["recipient"]["email"] == RECIPIENT_EMAIL


def test_share_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/shares/files/{uuid.uuid4()}",
        json={"recipient_email": RECIPIENT_EMAIL},
    )

    assert response.status_code == 401


def test_share_nonexistent_file_not_found(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    _recipient_headers(client, register_user)

    response = _share(client, auth_headers, uuid.uuid4())

    assert response.status_code == 404


def test_cannot_share_file_with_owner(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers)

    response = _share(client, auth_headers, uploaded["id"], OWNER_EMAIL)

    assert response.status_code == 422


def test_share_with_unknown_recipient_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    uploaded = _upload(client, auth_headers)

    response = _share(client, auth_headers, uploaded["id"], "nobody@example.com")

    assert response.status_code == 404


def test_duplicate_share_conflict(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)

    first = _share(client, auth_headers, uploaded["id"])
    assert first.status_code == 201, first.text

    second = _share(client, auth_headers, uploaded["id"])
    assert second.status_code == 409


def test_list_shares_for_file(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    _share(client, auth_headers, uploaded["id"])

    response = client.get(
        f"/api/v1/shares/files/{uploaded['id']}", headers=auth_headers
    )

    assert response.status_code == 200
    shares = response.json()
    assert len(shares) == 1
    assert shares[0]["recipient"]["email"] == RECIPIENT_EMAIL


def test_list_shares_for_file_not_owned_not_found(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)

    response = client.get(
        f"/api/v1/shares/files/{uploaded['id']}", headers=recipient_headers
    )

    assert response.status_code == 404


def test_revoke_share(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    share = _share(client, auth_headers, uploaded["id"]).json()

    response = client.delete(f"/api/v1/shares/{share['id']}", headers=auth_headers)
    assert response.status_code == 204

    received = client.get(
        "/api/v1/shares/received/files", headers=recipient_headers
    ).json()
    assert received == []


def test_revoke_share_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/api/v1/shares/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404


def test_recipient_cannot_revoke_owners_share(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    share = _share(client, auth_headers, uploaded["id"]).json()

    response = client.delete(f"/api/v1/shares/{share['id']}", headers=recipient_headers)

    assert response.status_code == 404


def test_list_received_files(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    _share(client, auth_headers, uploaded["id"])

    response = client.get("/api/v1/shares/received/files", headers=recipient_headers)

    assert response.status_code == 200
    files = response.json()
    assert [f["id"] for f in files] == [uploaded["id"]]


def test_deleted_shared_file_excluded_from_received_list(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    _share(client, auth_headers, uploaded["id"])

    client.delete(f"/api/v1/files/{uploaded['id']}", headers=auth_headers)

    response = client.get("/api/v1/shares/received/files", headers=recipient_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_download_shared_file(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    _share(client, auth_headers, uploaded["id"])

    response = client.get(
        f"/api/v1/shares/received/files/{uploaded['id']}/download",
        headers=recipient_headers,
    )

    assert response.status_code == 200
    assert response.content == b"shared content"


def test_download_unshared_file_not_found(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)

    response = client.get(
        f"/api/v1/shares/received/files/{uploaded['id']}/download",
        headers=recipient_headers,
    )

    assert response.status_code == 404


def test_download_after_revoke_not_found(
    client: TestClient, auth_headers: dict[str, str], register_user
) -> None:
    recipient_headers = _recipient_headers(client, register_user)
    uploaded = _upload(client, auth_headers)
    share = _share(client, auth_headers, uploaded["id"]).json()
    client.delete(f"/api/v1/shares/{share['id']}", headers=auth_headers)

    response = client.get(
        f"/api/v1/shares/received/files/{uploaded['id']}/download",
        headers=recipient_headers,
    )

    assert response.status_code == 404
