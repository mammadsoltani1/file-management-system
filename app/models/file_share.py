from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileShare(Base):
    __tablename__ = "file_shares"
    __table_args__ = (
        UniqueConstraint(
            "file_id", "recipient_id", name="uq_file_shares_file_id_recipient_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    recipient_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    file = relationship("StoredFile", foreign_keys=[file_id], lazy="selectin")

    recipient = relationship("User", foreign_keys=[recipient_id], lazy="selectin")
