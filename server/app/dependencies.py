from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .db import SessionLocal
from .security import decode_access_token, decode_admin_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin-api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Invalid token",
      )

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_admin_user(
    token: str = Depends(admin_oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.AdminUser:
    payload = decode_admin_access_token(token)
    admin_id = payload.get("sub")
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    admin_user = (
        db.query(models.AdminUser)
        .filter(models.AdminUser.id == int(admin_id))
        .first()
    )
    if admin_user is None or not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user not found",
        )
    return admin_user
