from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db
from ..security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: schemas.SignUpRequest,
    db: Session = Depends(get_db),
) -> schemas.TokenResponse:
    existing = crud.get_user_by_login_id(db, payload.login_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 아이디입니다.",
        )

    user = crud.create_local_user(
        db,
        login_id=payload.login_id,
        password=payload.password,
        nickname=payload.nickname,
    )
    token = create_access_token(str(user.id))
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest,
    db: Session = Depends(get_db),
) -> schemas.TokenResponse:
    user = crud.authenticate_user(
        db,
        login_id=payload.login_id,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    token = create_access_token(str(user.id))
    return schemas.TokenResponse(access_token=token)
