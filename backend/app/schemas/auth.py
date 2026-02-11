"""Authentication schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(
        ..., description="Raw initData string from Telegram.WebApp.initData"
    )


class UserResponse(BaseModel):
    id: UUID
    first_name: str
    onboarding_complete: bool
    subscription_status: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserResponse
