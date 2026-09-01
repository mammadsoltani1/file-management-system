from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthSession(Base):
    """a server side refresh token session for one signed in client"""

    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    family_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    rotated_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("auth_sessions.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )

    revoked_reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, default=None
    )
