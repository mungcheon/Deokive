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


class GoodsCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ko: str
    name_ja: str | None = None
    name_en: str | None = None
    category: str
    character_name: str
    affiliation: str = ""
    series_name: str | None = None
    sub_series: str | None = None
    official_price_jpy: int | None = None
    barcode: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    source_store: str = ""
    release_date: str | None = None


class GoodsCatalogCreate(BaseModel):
    name_ko: str = Field(min_length=1, max_length=200)
    name_ja: str | None = Field(default=None, max_length=200)
    name_en: str | None = Field(default=None, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    character_name: str = Field(min_length=1, max_length=80)
    affiliation: str = Field(default="", max_length=80)
    series_name: str | None = Field(default=None, max_length=120)
    sub_series: str | None = Field(default=None, max_length=120)
    official_price_jpy: int | None = None
    barcode: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=500)
    source_store: str = Field(default="", max_length=120)
    release_date: str | None = Field(default=None, max_length=40)
