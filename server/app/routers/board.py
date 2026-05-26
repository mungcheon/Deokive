"""Shared community board API.

Board posts are global (not per-user): every device reads the same list,
which is the whole point of moving the board server-side. Read endpoints
are public; writing requires auth. Admins can post notices, approve
info-bot posts, and moderate (edit/delete) any post.

Visibility rule: non-admins only see `approved` posts. Info-bot imports
arrive unapproved and surface publicly only after an admin approves them.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_current_user, get_db
from ..schemas import (
    BoardCommentCreate,
    BoardCommentRead,
    BoardPostCreate,
    BoardPostRead,
    BoardPostUpdate,
)

router = APIRouter(prefix="/board", tags=["board"])


def _profile_name(db: Session, user: models.User) -> str:
    prof = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == user.id)
        .first()
    )
    if prof and prof.nickname.strip():
        return prof.nickname.strip()
    return user.login_id


# ── Posts ────────────────────────────────────────────────────────────────
@router.get("/posts", response_model=list[BoardPostRead])
def list_posts(
    tag: str | None = Query(default=None),
    include_pending: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[models.BoardPost]:
    stmt = db.query(models.BoardPost)
    # Public listing hides unapproved posts. `include_pending` is honored
    # only when the caller is an admin (checked in the admin endpoint); the
    # public route always filters to approved.
    if not include_pending:
        stmt = stmt.filter(models.BoardPost.approved.is_(True))
    if tag:
        stmt = stmt.filter(models.BoardPost.tag == tag)
    return (
        stmt.order_by(models.BoardPost.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/posts/pending", response_model=list[BoardPostRead])
def list_pending(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> list[models.BoardPost]:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return (
        db.query(models.BoardPost)
        .filter(models.BoardPost.approved.is_(False))
        .order_by(models.BoardPost.created_at.desc())
        .all()
    )


@router.get("/posts/{post_id}", response_model=BoardPostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> models.BoardPost:
    post = db.get(models.BoardPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    # Count a view on fetch.
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return post


@router.post("/posts", response_model=BoardPostRead, status_code=201)
def create_post(
    payload: BoardPostCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.BoardPost:
    # Only admins may post notice/info tags; everyone may post general.
    tag = payload.tag if payload.tag in {"notice", "info", "general"} else "general"
    if tag in {"notice", "info"} and not user.is_admin:
        tag = "general"
    post = models.BoardPost(
        tag=tag,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        author=_profile_name(db, user),
        author_user_id=user.id,
        source_url=payload.source_url,
        image_url=payload.image_url,
        approved=True,  # human-authored posts are visible immediately
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.patch("/posts/{post_id}", response_model=BoardPostRead)
def update_post(
    post_id: int,
    payload: BoardPostUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.BoardPost:
    post = db.get(models.BoardPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    if not user.is_admin and post.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="not your post")
    for field in ("tag", "title", "summary", "content", "source_url", "image_url"):
        value = getattr(payload, field)
        if value is not None:
            setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> None:
    post = db.get(models.BoardPost, post_id)
    if post is None:
        return
    if not user.is_admin and post.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="not your post")
    db.delete(post)
    db.commit()


@router.post("/posts/{post_id}/approve", response_model=BoardPostRead)
def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.BoardPost:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    post = db.get(models.BoardPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    post.approved = True
    db.commit()
    db.refresh(post)
    return post


# ── Likes ─────────────────────────────────────────────────────────────────
@router.post("/posts/{post_id}/like")
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> dict[str, object]:
    post = db.get(models.BoardPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    existing = (
        db.query(models.BoardLike)
        .filter(
            models.BoardLike.user_id == user.id,
            models.BoardLike.post_id == post_id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        liked = False
    else:
        db.add(models.BoardLike(user_id=user.id, post_id=post_id))
        post.like_count += 1
        liked = True
    db.commit()
    return {"liked": liked, "like_count": post.like_count}


# ── Comments ───────────────────────────────────────────────────────────────
@router.get("/posts/{post_id}/comments", response_model=list[BoardCommentRead])
def list_comments(
    post_id: int, db: Session = Depends(get_db)
) -> list[models.BoardComment]:
    return (
        db.query(models.BoardComment)
        .filter(models.BoardComment.post_id == post_id)
        .order_by(models.BoardComment.created_at.asc())
        .all()
    )


@router.post(
    "/posts/{post_id}/comments", response_model=BoardCommentRead, status_code=201
)
def add_comment(
    post_id: int,
    payload: BoardCommentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.BoardComment:
    post = db.get(models.BoardPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    comment = models.BoardComment(
        post_id=post_id,
        author=_profile_name(db, user),
        author_user_id=user.id,
        content=payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> None:
    comment = db.get(models.BoardComment, comment_id)
    if comment is None:
        return
    if not user.is_admin and comment.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="not your comment")
    db.delete(comment)
    db.commit()
