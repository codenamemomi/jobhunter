"""Application tracker model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Allowed pipeline statuses
APPLICATION_STATUSES = (
    "wishlist",
    "draft",
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="wishlist", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Phase B: email-apply package
    apply_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)  # email | url | manual
    email_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    send_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_auto: Mapped[bool] = mapped_column(default=False)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
