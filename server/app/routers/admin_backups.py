from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_current_admin_user, get_db

router = APIRouter(prefix="/admin-api/v1/backups", tags=["admin-backups"])


@router.get("", response_model=list[schemas.AdminBackupListItem])
def list_backups(
    _: object = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[schemas.AdminBackupListItem]:
    rows = crud.list_backup_snapshots(db, limit=limit)
    items: list[schemas.AdminBackupListItem] = []
    for snapshot, user, profile in rows:
        login_id = user.login_id if user is not None else f"user:{snapshot.user_id}"
        nickname = profile.nickname if profile is not None else "Unknown"
        items.append(
            schemas.AdminBackupListItem(
                user_id=snapshot.user_id,
                login_id=login_id,
                nickname=nickname,
                source=snapshot.source,
                payload_bytes=len(snapshot.payload_json.encode("utf-8")),
                uploaded_at=snapshot.updated_at.isoformat(),
            )
        )
    return items
