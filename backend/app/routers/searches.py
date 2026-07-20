"""Saved search routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.schemas.saved_search import SavedSearchCreate, SavedSearchOut, SavedSearchUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/searches", tags=["searches"])


@router.get("", response_model=list[SavedSearchOut])
def list_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SavedSearch]:
    return (
        db.query(SavedSearch)
        .filter(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )


@router.post("", response_model=SavedSearchOut, status_code=201)
def create_search(
    payload: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    search = SavedSearch(user_id=current_user.id, **payload.model_dump())
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.get("/{search_id}", response_model=SavedSearchOut)
def get_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    search = _owned_search(db, current_user.id, search_id)
    return search


@router.patch("/{search_id}", response_model=SavedSearchOut)
def update_search(
    search_id: int,
    payload: SavedSearchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    search = _owned_search(db, current_user.id, search_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(search, key, value)
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.delete("/{search_id}", status_code=204)
def delete_search(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    search = _owned_search(db, current_user.id, search_id)
    db.delete(search)
    db.commit()


def _owned_search(db: Session, user_id: int, search_id: int) -> SavedSearch:
    search = (
        db.query(SavedSearch)
        .filter(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
        .first()
    )
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search
