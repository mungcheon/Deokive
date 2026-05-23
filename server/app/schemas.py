from pydantic import BaseModel, ConfigDict, Field


class SignUpRequest(BaseModel):
    login_id: str = Field(min_length=4, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(min_length=1, max_length=40)


class LoginRequest(BaseModel):
    login_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    login_id: str
    nickname: str
    tag: str
    provider: str
    google_email: str | None = None
    profile_image_url: str | None = None
    is_premium: bool


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=40)
    tag: str | None = Field(default=None, min_length=2, max_length=40)
    profile_image_url: str | None = Field(default=None, max_length=500)
