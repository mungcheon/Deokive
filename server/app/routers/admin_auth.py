from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_current_admin_user, get_db
from ..security import create_admin_access_token

router = APIRouter(prefix="/admin-api/v1/auth", tags=["admin-auth"])


@router.post("/login", response_model=schemas.AdminTokenResponse)
def admin_login(
    payload: schemas.AdminLoginRequest,
    db: Session = Depends(get_db),
) -> schemas.AdminTokenResponse:
    admin_user = crud.authenticate_admin_user(
        db,
        email=payload.login_id.strip().lower(),
        password=payload.password,
    )
    if admin_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    token = create_admin_access_token(str(admin_user.id))
    return schemas.AdminTokenResponse(
        access_token=token,
        role=admin_user.role,
        display_name=admin_user.display_name,
    )


@router.get("/me", response_model=schemas.AdminProfileResponse)
def admin_me(
    current_admin = Depends(get_current_admin_user),
) -> schemas.AdminProfileResponse:
    return schemas.AdminProfileResponse(
        admin_id=current_admin.id,
        email=current_admin.email,
        display_name=current_admin.display_name,
        role=current_admin.role,
        is_active=current_admin.is_active,
    )
