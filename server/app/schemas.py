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


class HomeBannerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subtitle: str = ""
    body: str = ""
    icon_name: str = "campaign_rounded"
    image_url: str | None = None
    link_url: str | None = None
    sort_order: int = 0


class HomeBannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=300)
    body: str = Field(default="", max_length=20000)
    icon_name: str = Field(default="campaign_rounded", max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    sort_order: int = 0


class HomeBannerUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    body: str | None = Field(default=None, max_length=20000)
    icon_name: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


class BoardCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    author: str
    content: str


class BoardCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class BoardPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    title: str
    summary: str = ""
    content: str = ""
    author: str
    author_user_id: int | None = None
    source_url: str | None = None
    image_url: str | None = None
    view_count: int = 0
    like_count: int = 0
    approved: bool = True


class BoardPostCreate(BaseModel):
    tag: str = Field(default="general", max_length=20)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=300)
    content: str = Field(default="", max_length=20000)
    source_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)


class BoardPostUpdate(BaseModel):
    tag: str | None = Field(default=None, max_length=20)
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=300)
    content: str | None = Field(default=None, max_length=20000)
    source_url: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=500)


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
