from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str] = mapped_column(String(20), default="local")
    google_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    # Board moderation: only admins can post notices, approve info-bot posts,
    # and edit/delete others' posts.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    folders: Mapped[list["Folder"]] = relationship(back_populates="user")
    goods: Mapped[list["Goods"]] = relationship(back_populates="user")
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("tag", name="uq_profiles_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    nickname: Mapped[str] = mapped_column(String(40))
    tag: Mapped[str] = mapped_column(String(40))
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")


class Folder(Base, TimestampMixin):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    color_hex: Mapped[str] = mapped_column(String(16), default="#87CEEB")
    icon_name: Mapped[str] = mapped_column(String(80), default="folder_rounded")

    user: Mapped[User] = relationship(back_populates="folders")


class Goods(Base, TimestampMixin):
    __tablename__ = "goods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    series_name: Mapped[str] = mapped_column(String(120), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    official_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purchase_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purchase_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="보관중")
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    storage_location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="goods")


class CalendarEvent(Base, TimestampMixin):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(20), default="personal")
    event_date: Mapped[str] = mapped_column(String(40))
    time_text: Mapped[str | None] = mapped_column(String(40), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="calendar_events")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="iap")
    product_id: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="active")
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="KRW")

    user: Mapped[User] = relationship(back_populates="payments")


class HomeBanner(Base, TimestampMixin):
    """Home-screen banner / announcement slide, editable by admins from any
    device. Replaces the hardcoded tutorial slides once the server is live —
    the app fetches and caches these so admins can update them without an app
    release."""

    __tablename__ = "home_banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    icon_name: Mapped[str] = mapped_column(String(80), default="campaign_rounded")
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BoardPost(Base, TimestampMixin):
    """Shared community board post. Unlike per-user goods/folders, board
    posts are global — every device reads the same list. Info-bot-fetched
    posts arrive with approved=False and surface publicly only after an
    admin approves them; user/admin-authored posts default to approved."""

    __tablename__ = "board_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # tag: notice / info / general
    tag: Mapped[str] = mapped_column(String(20), default="general", index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(80), default="관리자")
    # Null for system/info-bot posts; set for user-authored posts so we can
    # authorize edits/deletes.
    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    approved: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    comments: Mapped[list["BoardComment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class BoardComment(Base, TimestampMixin):
    __tablename__ = "board_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("board_posts.id"), index=True
    )
    author: Mapped[str] = mapped_column(String(80), default="익명")
    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text)

    post: Mapped[BoardPost] = relationship(back_populates="comments")


class BoardLike(Base):
    """One row per (user, post) like. Composite-unique so a user can't
    double-like; deleting a row = unlike."""

    __tablename__ = "board_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_board_like"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("board_posts.id"), index=True)


class GoodsCatalog(Base, TimestampMixin):
    """Editor-curated catalog of goods. Searched by autocomplete on the
    client when users add their own goods. Multiple language fields let the
    client display localized names while keeping a single canonical entry."""

    __tablename__ = "goods_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_ko: Mapped[str] = mapped_column(String(200), index=True)
    name_ja: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    character_name: Mapped[str] = mapped_column(String(80), index=True)
    affiliation: Mapped[str] = mapped_column(String(80), default="")
    series_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sub_series: Mapped[str | None] = mapped_column(String(120), nullable=True)
    official_price_jpy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_store: Mapped[str] = mapped_column(String(120), default="")
    release_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
