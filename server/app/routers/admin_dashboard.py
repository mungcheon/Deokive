from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_current_admin_user, get_db

router = APIRouter(prefix="/admin-api/v1/dashboard", tags=["admin-dashboard"])


@router.get("/summary", response_model=schemas.AdminDashboardSummaryResponse)
def dashboard_summary(
    _: object = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> schemas.AdminDashboardSummaryResponse:
    backup_count = crud.count_backup_snapshots(db)
    return schemas.AdminDashboardSummaryResponse(
        total_users=crud.count_users(db),
        local_users=crud.count_users_by_provider(db, provider="local"),
        google_users=crud.count_users_by_provider(db, provider="google"),
        premium_users=crud.count_premium_users(db),
        backup_snapshot_count=backup_count,
        active_backup_users=backup_count,
        pending_support_count=0,
        catalog_item_count=0,
    )
