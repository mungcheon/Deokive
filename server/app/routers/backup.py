import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(prefix="/backup", tags=["backup"])


def _snapshot_response(
    snapshot: models.BackupSnapshot,
    *,
    include_payload: bool,
) -> schemas.BackupSnapshotResponse:
    payload = json.loads(snapshot.payload_json)
    return schemas.BackupSnapshotResponse(
        source=snapshot.source,
        uploaded_at=snapshot.updated_at.isoformat(),
        payload_bytes=len(snapshot.payload_json.encode("utf-8")),
        payload=payload if include_payload else None,
    )


@router.get("/snapshot", response_model=schemas.BackupSnapshotResponse)
def get_snapshot(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.BackupSnapshotResponse:
    snapshot = crud.get_backup_snapshot(db, user_id=current_user.id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup snapshot not found.",
        )
    return _snapshot_response(snapshot, include_payload=True)


@router.put("/snapshot", response_model=schemas.BackupSnapshotResponse)
def upsert_snapshot(
    payload: schemas.BackupSnapshotUpsertRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.BackupSnapshotResponse:
    snapshot = crud.upsert_backup_snapshot(
        db,
        user_id=current_user.id,
        source=payload.source,
        payload=payload.payload,
    )
    return _snapshot_response(snapshot, include_payload=False)
