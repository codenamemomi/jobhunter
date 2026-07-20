"""User model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Phase D: auto-apply preferences (email-apply only)
    auto_draft_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_send_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_min_score: Mapped[float] = mapped_column(Float, default=75.0)
    auto_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    auto_prefer_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_email_only: Mapped[bool] = mapped_column(Boolean, default=True)

    saved_searches = relationship("SavedSearch", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    cv = relationship("CV", back_populates="user", uselist=False, cascade="all, delete-orphan")
