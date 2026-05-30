from . import models
from .core.config import settings
from .crud import create_local_user, get_user_by_login_id
from .db import Base, SessionLocal, engine


def ensure_database_ready() -> None:
    Base.metadata.create_all(bind=engine)


def ensure_sole_admin() -> tuple[str, str] | None:
    db = SessionLocal()
    try:
        admin_id = settings.sole_admin_login_id
        admin_pw = settings.sole_admin_password
        admin_nickname = settings.sole_admin_nickname
        user = get_user_by_login_id(db, admin_id)
        created = False
        if user is None:
            create_local_user(
                db,
                login_id=admin_id,
                password=admin_pw,
                nickname=admin_nickname,
            )
            created = True

        for other in db.query(models.User).all():
            other.is_admin = other.login_id == admin_id
        db.commit()
        return (admin_id, admin_pw) if created else None
    finally:
        db.close()
