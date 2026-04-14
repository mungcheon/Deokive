from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_current_admin_user, get_db

router = APIRouter(prefix="/admin-api/v1/users", tags=["admin-users"])


@router.get("", response_model=list[schemas.AdminUserListItem])
def list_users(
    _: object = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[schemas.AdminUserListItem]:
    users = crud.list_users(db, limit=limit)
    return [
        schemas.AdminUserListItem(
            user_id=user.id,
            login_id=user.login_id,
            nickname=user.profile.nickname,
            tag=user.profile.tag,
            provider=user.provider,
            google_email=user.google_email,
            is_premium=user.is_premium,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]
