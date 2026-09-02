import logging
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryUnavailableError(Exception):
    """raised when email delivery is unavailable"""


class EmailService:
    def _validate_configuration(self) -> None:
        if not settings.RESEND_API_KEY:
            raise EmailDeliveryUnavailableError("RESEND API KEY is not configured")
        if not settings.EMAIL_FROM_ADDRESS:
            raise EmailDeliveryUnavailableError("EMAIL FROM ADDRESS is not configured")

    async def send_verification_email(
        self, recipient: str, verification_token: str
    ) -> None:
        """send an email verification link through resend's http api"""

        self._validate_configuration()
        query = urlencode({"token": verification_token})
        verification_url = f"{settings.EMAIL_VERIFICATION_FRONTEND_URL}?{query}"

        sender = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"

        payload = {
            "from": sender,
            "to": [recipient],
            "subject": "verify your email address",
            "text": f"hi \n\nverify your email address by opening this link \n{verification_url}\n\nthis verification link expires at {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} hours\nignore if it was not you who made an account",
            "html": f"""\
                <!doctype html>
                <html lang="en">
                <body>
                    <p>hi,</p>
                    <p>verify your email address by opening this link </p>
                    <p>
                    <a
                        href="{verification_url}"
                        style="
                        display: inline-block;
                        padding: 12px 18px;
                        background: #2563eb;
                        color: #ffffff;
                        text-decoration: none;
                        border-radius: 6px;
                        font-family: Arial, sans-serif;
                        "
                    >
                        verify email address
                    </a>
                    </p>
                    <p>
                    this verification link expires at {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} hours
                    </p>
                    <p>ignore if it was not you who made an account
                    </p>
                </body>
                </html>
                """,
        }
        headers = {
            "authorization": f"bearer {settings.RESEND_API_KEY}",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.EMAIL_TIMEOUT_SECONDS
            ) as client:
                res = await client.post(
                    settings.RESEND_API_URL, json=payload, headers=headers
                )
                res.raise_for_status()
        except httpx.HTTPStatusError as err:
            logger.error(
                "resend rejected verification email for %s: %s %s",
                recipient,
                err.response.status_code,
                err.response.text,
            )
            raise EmailDeliveryUnavailableError(
                "email provider rejected the verification email"
            ) from err

        except httpx.RequestError as err:
            logger.error(
                "could not reach resend for verification email to %s: %s",
                recipient,
                err,
            )
            raise EmailDeliveryUnavailableError(
                "could not reach the email provider"
            ) from err
