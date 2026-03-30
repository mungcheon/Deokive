from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(tags=["profile"])


def _profile_response(user: models.User) -> schemas.ProfileResponse:
    profile = user.profile
    return schemas.ProfileResponse(
        user_id=user.id,
        login_id=user.login_id,
        nickname=profile.nickname,
        tag=profile.tag,
        provider=user.provider,
        google_email=user.google_email,
        profile_image_url=profile.profile_image_url,
        is_premium=user.is_premium,
    )


@router.get("/me", response_model=schemas.ProfileResponse)
def get_me(current_user: models.User = Depends(get_current_user)) -> schemas.ProfileResponse:
    return _profile_response(current_user)


@router.patch("/me", response_model=schemas.ProfileResponse)
def update_me(
    payload: schemas.ProfileUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ProfileResponse:
    profile = current_user.profile

    if payload.nickname is not None:
        profile.nickname = payload.nickname.strip()

    if payload.tag is not None:
        normalized_tag = payload.tag.strip()
        if not normalized_tag.startswith("@"):
            normalized_tag = f"@{normalized_tag}"

        duplicate = crud.get_profile_by_tag(db, normalized_tag)
        if duplicate is not None and duplicate.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 태그입니다.",
            )
        profile.tag = normalized_tag

    if payload.profile_image_url is not None:
        profile.profile_image_url = payload.profile_image_url.strip() or None

    db.add(profile)
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user)
