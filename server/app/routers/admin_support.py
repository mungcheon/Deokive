from fastapi import APIRouter, Depends

from .. import schemas
from ..dependencies import get_current_admin_user

router = APIRouter(prefix="/admin-api/v1/support", tags=["admin-support"])


@router.get("/tickets", response_model=list[schemas.SupportTicketListItem])
def list_support_tickets(
    _: object = Depends(get_current_admin_user),
) -> list[schemas.SupportTicketListItem]:
    return []
