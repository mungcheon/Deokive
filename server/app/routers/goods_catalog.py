"""Public read API for the editor-curated goods catalog.

Designed for the autocomplete and "find existing product" flows on the
client: anyone can search/list/get; only the seed script (or future admin
endpoint) writes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import GoodsCatalog
from ..schemas import GoodsCatalogRead

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/search", response_model=list[GoodsCatalogRead])
def search(
    q: str | None = Query(default=None, description="Substring across ko/ja/en name"),
    character: str | None = Query(default=None),
    category: str | None = Query(default=None),
    affiliation: str | None = Query(default=None),
    series_name: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(_db),
) -> list[GoodsCatalog]:
    stmt = db.query(GoodsCatalog).filter(GoodsCatalog.is_active.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.filter(
            or_(
                GoodsCatalog.name_ko.ilike(pattern),
                GoodsCatalog.name_ja.ilike(pattern),
                GoodsCatalog.name_en.ilike(pattern),
                GoodsCatalog.series_name.ilike(pattern),
                GoodsCatalog.character_name.ilike(pattern),
            )
        )
    if character:
        stmt = stmt.filter(GoodsCatalog.character_name == character)
    if category:
        stmt = stmt.filter(GoodsCatalog.category == category)
    if affiliation:
        stmt = stmt.filter(GoodsCatalog.affiliation == affiliation)
    if series_name:
        stmt = stmt.filter(GoodsCatalog.series_name == series_name)
    return stmt.order_by(GoodsCatalog.id.desc()).limit(limit).all()


@router.get("/by-barcode/{barcode}", response_model=GoodsCatalogRead)
def by_barcode(barcode: str, db: Session = Depends(_db)) -> GoodsCatalog:
    item = (
        db.query(GoodsCatalog)
        .filter(GoodsCatalog.barcode == barcode, GoodsCatalog.is_active.is_(True))
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="catalog item not found")
    return item


@router.get("/characters", response_model=list[str])
def characters(db: Session = Depends(_db)) -> list[str]:
    rows = (
        db.query(GoodsCatalog.character_name)
        .filter(GoodsCatalog.is_active.is_(True))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


@router.get("/categories", response_model=list[str])
def categories(db: Session = Depends(_db)) -> list[str]:
    rows = (
        db.query(GoodsCatalog.category)
        .filter(GoodsCatalog.is_active.is_(True))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


@router.get("/series", response_model=list[str])
def series(db: Session = Depends(_db)) -> list[str]:
    rows = (
        db.query(GoodsCatalog.series_name)
        .filter(GoodsCatalog.is_active.is_(True))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


@router.get("/{item_id}", response_model=GoodsCatalogRead)
def get_one(item_id: int, db: Session = Depends(_db)) -> GoodsCatalog:
    item = db.query(GoodsCatalog).filter(GoodsCatalog.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="catalog item not found")
    return item
