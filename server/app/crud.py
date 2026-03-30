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
