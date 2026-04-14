from fastapi import APIRouter, Depends

from .. import schemas
from ..dependencies import get_current_admin_user

router = APIRouter(prefix="/admin-api/v1/catalog", tags=["admin-catalog"])


@router.get("/items", response_model=list[schemas.CatalogItemListItem])
def list_catalog_items(
    _: object = Depends(get_current_admin_user),
) -> list[schemas.CatalogItemListItem]:
    return []
