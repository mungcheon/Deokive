"""Home-screen banner API.

Public read (the app fetches active banners for the home carousel). Writes
are admin-only — so an admin can edit the home banners from any device and
all users see the update without an app release.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_current_user, get_db, require_admin
from ..schemas import HomeBannerCreate, HomeBannerRead, HomeBannerUpdate

router = APIRouter(prefix="/banners", tags=["banners"])


@router.get("", response_model=list[HomeBannerRead])
def list_banners(db: Session = Depends(get_db)) -> list[models.HomeBanner]:
    return (
        db.query(models.HomeBanner)
        .filter(models.HomeBanner.is_active.is_(True))
        .order_by(models.HomeBanner.sort_order.asc(), models.HomeBanner.id.asc())
        .all()
    )


@router.post("", response_model=HomeBannerRead, status_code=201)
def create_banner(
    payload: HomeBannerCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.HomeBanner:
    require_admin(user)
    banner = models.HomeBanner(**payload.model_dump())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.patch("/{banner_id}", response_model=HomeBannerRead)
def update_banner(
    banner_id: int,
    payload: HomeBannerUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.HomeBanner:
    require_admin(user)
    banner = db.get(models.HomeBanner, banner_id)
    if banner is None:
        raise HTTPException(status_code=404, detail="banner not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    db.commit()
    db.refresh(banner)
    return banner


@router.delete("/{banner_id}", status_code=204)
def delete_banner(
    banner_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> None:
    require_admin(user)
    banner = db.get(models.HomeBanner, banner_id)
    if banner is None:
        return
    db.delete(banner)
    db.commit()
