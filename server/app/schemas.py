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


class BackupSnapshotUpsertRequest(BaseModel):
    source: str = Field(default="manual")
    payload: dict


class BackupSnapshotResponse(BaseModel):
    source: str
    uploaded_at: str
    payload_bytes: int
    payload: dict | None = None


class AdminLoginRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str


class AdminProfileResponse(BaseModel):
    admin_id: int
    email: str
    display_name: str
    role: str
    is_active: bool


class AdminDashboardSummaryResponse(BaseModel):
    total_users: int
    local_users: int
    google_users: int
    premium_users: int
    backup_snapshot_count: int
    active_backup_users: int
    pending_support_count: int
    catalog_item_count: int


class AdminUserListItem(BaseModel):
    user_id: int
    login_id: str
    nickname: str
    tag: str
    provider: str
    google_email: str | None = None
    is_premium: bool
    created_at: str


class AdminBackupListItem(BaseModel):
    user_id: int
    login_id: str
    nickname: str
    source: str
    payload_bytes: int
    uploaded_at: str


class SupportTicketListItem(BaseModel):
    ticket_id: str
    title: str
    status: str
    created_at: str


class CatalogItemListItem(BaseModel):
    item_id: str
    name: str
    status: str
    updated_at: str
