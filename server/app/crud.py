import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import models
from .security import hash_password, verify_password


def generate_default_tag(db: Session) -> str:
    last_profile = (
        db.query(models.Profile)
        .order_by(models.Profile.id.desc())
        .first()
    )
    next_number = 1 if last_profile is None else last_profile.id + 1
    return f"@deokive{next_number}"


def get_user_by_login_id(db: Session, login_id: str) -> models.User | None:
    return db.query(models.User).filter(models.User.login_id == login_id).first()


def get_profile_by_tag(db: Session, tag: str) -> models.Profile | None:
    return db.query(models.Profile).filter(models.Profile.tag == tag).first()


def create_local_user(
    db: Session,
    *,
    login_id: str,
    password: str,
    nickname: str,
) -> models.User:
    user = models.User(
        login_id=login_id,
        password_hash=hash_password(password),
        provider="local",
    )
    db.add(user)
    db.flush()

    profile = models.Profile(
        user_id=user.id,
        nickname=nickname,
        tag=generate_default_tag(db),
    )
    db.add(profile)

    root_folder = models.Folder(
        user_id=user.id,
        name="기본 폴더",
        is_group=False,
    )
    db.add(root_folder)

    db.commit()
    db.refresh(user)
    db.refresh(profile)
    return user


def authenticate_user(
    db: Session,
    *,
    login_id: str,
    password: str,
) -> models.User | None:
    user = get_user_by_login_id(db, login_id)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_backup_snapshot(
    db: Session,
    *,
    user_id: int,
) -> models.BackupSnapshot | None:
    return (
        db.query(models.BackupSnapshot)
        .filter(models.BackupSnapshot.user_id == user_id)
        .first()
    )


def upsert_backup_snapshot(
    db: Session,
    *,
    user_id: int,
    source: str,
    payload: dict,
) -> models.BackupSnapshot:
    snapshot = get_backup_snapshot(db, user_id=user_id)
    payload_json = json.dumps(payload, ensure_ascii=False)

    if snapshot is None:
        snapshot = models.BackupSnapshot(
            user_id=user_id,
            source=source,
            payload_json=payload_json,
        )
    else:
        snapshot.source = source
        snapshot.payload_json = payload_json

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_admin_user_by_email(
    db: Session,
    *,
    email: str,
) -> models.AdminUser | None:
    return db.query(models.AdminUser).filter(models.AdminUser.email == email).first()


def authenticate_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> models.AdminUser | None:
    admin_user = get_admin_user_by_email(db, email=email)
    if admin_user is None or not admin_user.is_active:
        return None
    if not verify_password(password, admin_user.password_hash):
        return None

    admin_user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def create_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str,
    role: str = "super_admin",
) -> models.AdminUser:
    admin_user = models.AdminUser(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    return admin_user


def ensure_bootstrap_admin(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str,
) -> None:
    normalized_email = email.strip().lower()
    if not normalized_email or not password.strip():
        return
    existing = get_admin_user_by_email(db, email=normalized_email)
    if existing is not None:
        existing.password_hash = hash_password(password)
        existing.display_name = display_name.strip() or existing.display_name
        existing.is_active = True
        db.add(existing)
        db.commit()
        return
    create_admin_user(
        db,
        email=normalized_email,
        password=password,
        display_name=display_name.strip() or "Deokive Admin",
    )


def list_users(db: Session, *, limit: int = 50) -> list[models.User]:
    return (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .limit(limit)
        .all()
    )


def list_backup_snapshots(
    db: Session,
    *,
    limit: int = 50,
) -> list[tuple[models.BackupSnapshot, models.User | None, models.Profile | None]]:
    rows = (
        db.query(models.BackupSnapshot, models.User, models.Profile)
        .outerjoin(models.User, models.User.id == models.BackupSnapshot.user_id)
        .outerjoin(models.Profile, models.Profile.user_id == models.BackupSnapshot.user_id)
        .order_by(models.BackupSnapshot.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        (
            snapshot,
            user,
            profile,
        )
        for snapshot, user, profile in rows
    ]


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def count_users_by_provider(db: Session, *, provider: str) -> int:
    return db.query(models.User).filter(models.User.provider == provider).count()


def count_premium_users(db: Session) -> int:
    return db.query(models.User).filter(models.User.is_premium.is_(True)).count()


def count_backup_snapshots(db: Session) -> int:
    return db.query(models.BackupSnapshot).count()
