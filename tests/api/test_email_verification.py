import pytest
from fastapi.testclient import TestClient

import app.services.email_service as email_service_module
from app.services.email_service import EmailDeliveryUnavailableError


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    captured: list[dict[str, str]] = []

    async def fake_send(self, recipient: str, verification_token: str) -> None:
        captured.append({"recipient": recipient, "token": verification_token})

    monkeypatch.setattr(
        email_service_module.EmailService, "send_verification_email", fake_send
    )
    return captured


def test_request_email_verification_sends_email(
    client: TestClient, auth_headers: dict[str, str], sent_emails: list[dict[str, str]]
) -> None:
    response = client.post(
        "/api/v1/auth/email-verification/request", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() == {"verified": False}
    assert len(sent_emails) == 1
    assert sent_emails[0]["recipient"] == "test@example.com"
    assert sent_emails[0]["token"]


def test_request_email_verification_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/auth/email-verification/request")

    assert response.status_code == 401


def test_request_email_verification_already_verified_sends_no_email(
    client: TestClient, auth_headers: dict[str, str], sent_emails: list[dict[str, str]]
) -> None:
    first = client.post(
        "/api/v1/auth/email-verification/request", headers=auth_headers
    ).json()
    token = sent_emails[0]["token"]
    client.post("/api/v1/auth/email-verification/confirm", json={"token": token})

    response = client.post(
        "/api/v1/auth/email-verification/request", headers=auth_headers
    )

    assert first == {"verified": False}
    assert response.status_code == 200
    assert response.json() == {"verified": True}
    assert len(sent_emails) == 1


def test_confirm_email_verification_marks_user_verified(
    client: TestClient, auth_headers: dict[str, str], sent_emails: list[dict[str, str]]
) -> None:
    client.post("/api/v1/auth/email-verification/request", headers=auth_headers)
    token = sent_emails[0]["token"]

    response = client.post(
        "/api/v1/auth/email-verification/confirm", json={"token": token}
    )

    assert response.status_code == 200
    assert response.json() == {"verified": True}

    follow_up = client.post(
        "/api/v1/auth/email-verification/request", headers=auth_headers
    )
    assert follow_up.json() == {"verified": True}


def test_confirm_email_verification_rejects_reused_token(
    client: TestClient, auth_headers: dict[str, str], sent_emails: list[dict[str, str]]
) -> None:
    client.post("/api/v1/auth/email-verification/request", headers=auth_headers)
    token = sent_emails[0]["token"]

    client.post("/api/v1/auth/email-verification/confirm", json={"token": token})
    response = client.post(
        "/api/v1/auth/email-verification/confirm", json={"token": token}
    )

    assert response.status_code == 400


def test_confirm_email_verification_rejects_unknown_token(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/email-verification/confirm",
        json={"token": "x" * 32},
    )

    assert response.status_code == 400


def test_confirm_email_verification_rejects_too_short_token(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/email-verification/confirm",
        json={"token": "short"},
    )

    assert response.status_code == 422


def test_request_email_verification_delivery_failure_returns_503(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_send(self, recipient: str, verification_token: str) -> None:
        raise EmailDeliveryUnavailableError("provider unreachable")

    monkeypatch.setattr(
        email_service_module.EmailService, "send_verification_email", failing_send
    )

    response = client.post(
        "/api/v1/auth/email-verification/request", headers=auth_headers
    )

    assert response.status_code == 503


def test_requesting_a_new_token_invalidates_the_previous_one(
    client: TestClient, auth_headers: dict[str, str], sent_emails: list[dict[str, str]]
) -> None:
    client.post("/api/v1/auth/email-verification/request", headers=auth_headers)
    first_token = sent_emails[0]["token"]

    client.post("/api/v1/auth/email-verification/request", headers=auth_headers)
    second_token = sent_emails[1]["token"]

    stale_response = client.post(
        "/api/v1/auth/email-verification/confirm", json={"token": first_token}
    )
    fresh_response = client.post(
        "/api/v1/auth/email-verification/confirm", json={"token": second_token}
    )

    assert stale_response.status_code == 400
    assert fresh_response.status_code == 200
