"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    auto_draft_enabled: bool = False
    auto_send_enabled: bool = False
    auto_min_score: float = 75.0
    auto_daily_limit: int = 5
    auto_prefer_remote: bool = True
    auto_email_only: bool = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
