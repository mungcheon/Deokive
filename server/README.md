# Deokive Server

Deokive 운영 단계용 백엔드 골격입니다.

개발 기본값:
- FastAPI
- SQLite
- SQLAlchemy
- JWT 인증

운영 전환 권장:
- PostgreSQL
- S3 또는 Cloudflare R2
- Redis

## 실행 순서

1. 가상환경 생성
2. `pip install -r requirements.txt`
3. `.env.example`를 `.env`로 복사
4. `python init_sqlite_db.py`
5. `uvicorn app.main:app --reload`

## 기본 엔드포인트

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `GET /me`
- `PATCH /me`

## 기본 계정 구조

- 일반 로그인: `login_id + password`
- 구글 로그인: 추후 OAuth 토큰 검증 로직 추가
- 태그: `@deokive1` 형태 기본 생성, 이후 수정 가능
