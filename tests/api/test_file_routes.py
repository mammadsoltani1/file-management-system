from fastapi.testclient import TestClient


def test_file_routes_are_in_openapi_schema(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/files/upload" in paths
    assert "post" in paths["/api/v1/files/upload"]

    assert "/api/v1/files" in paths
    assert "get" in paths["/api/v1/files"]

    assert "/api/v1/files/{file_id}/download" in paths
    assert "get" in paths["/api/v1/files/{file_id}/download"]

    assert "/api/v1/files/{file_id}" in paths
    assert "delete" in paths["/api/v1/files/{file_id}"]
