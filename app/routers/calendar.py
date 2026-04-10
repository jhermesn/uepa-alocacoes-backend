from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.try_database import get_db
from app.services.rbac import require_role
from app.services.google_calendar import list_events, create_event, update_event, delete_event
from pydantic import BaseModel
from app.repositories.cache_repository import CacheRepository
from app.config import get_settings

router = APIRouter(prefix="/calendar", tags=["calendar"])
PLATFORM_EVENT_SOURCE = "alocacoes"


def _is_platform_event(event: dict) -> bool:
    priv = (event.get("extendedProperties") or {}).get("private") or {}
    if priv.get("platform_source") == PLATFORM_EVENT_SOURCE:
        return True
    return bool(priv.get("fk_sala") and priv.get("fk_usuario"))


@router.get("/events")
def get_calendar_events(
    db: Session = Depends(get_db),
    _u=Depends(require_role(1)),
    view: str = Query("month", pattern="^(day|week|month|semester)$"),
    anchor: Optional[datetime] = Query(None),
    room_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
):
    center = anchor or datetime.utcnow()
    if view == "day":
        start = center.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif view == "week":
        start = center - timedelta(days=center.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
    elif view == "semester":
        start = center - timedelta(days=90)
        end = center + timedelta(days=90)
    else:
        start = center.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month
    items = list_events(db=db, user_id=_u.id, time_min_utc=start, time_max_utc=end)
    if items is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google credentials not connected")
    result = []
    for ev in items:
        if not _is_platform_event(ev):
            continue
        priv = (ev.get("extendedProperties") or {}).get("private") or {}
        if room_id is not None and str(priv.get("fk_sala")) != str(room_id):
            continue
        if user_id is not None and str(priv.get("fk_usuario")) != str(user_id):
            continue
        result.append(ev)
    return {"items": result}


class GoogleEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_dt_utc: datetime
    end_dt_utc: datetime
    location: Optional[str] = None
    calendar_id: Optional[str] = None


class GoogleEventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    start_dt_utc: Optional[datetime] = None
    end_dt_utc: Optional[datetime] = None
    location: Optional[str] = None
    calendar_id: Optional[str] = None


@router.get("/google/events")
def google_list_events(
    db: Session = Depends(get_db),
    _u=Depends(require_role(1)),
    start: datetime = Query(...),
    end: datetime = Query(...),
    calendar_id: Optional[str] = Query(None),
    force_refresh: bool = Query(False),
    settings=Depends(get_settings)
):
    # cache logic
    cache_repo = CacheRepository(db)
    cache_key = cache_repo.generate_key(
        "google_sync", 
        user_id=_u.id, 
        start=start.isoformat(), 
        end=end.isoformat(), 
        cal=calendar_id or "primary"
    )
    if not force_refresh:
        cached_items = cache_repo.get(cache_key)
        if cached_items is not None:
            return {"items": cached_items, "cached": True}

    # cache miss
    items = list_events(db=db, user_id=_u.id, time_min_utc=start, time_max_utc=end, calendar_id=calendar_id)
    if items is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google credentials not connected")

    filtered_items = [item for item in items if _is_platform_event(item)]
    cache_repo.set(cache_key, filtered_items, ttl=settings.CACHE_TTL_STRICT)

    return {"items": filtered_items, "cached": False}


@router.post("/google/events", status_code=status.HTTP_201_CREATED)
def google_create_event(payload: GoogleEventCreate, db: Session = Depends(get_db), _u=Depends(require_role(1))):
    CacheRepository(db).invalidate_pattern(f"google_sync_user_id:{_u.id}")
    evt = create_event(
        db=db,
        user_id=_u.id,
        summary=payload.summary,
        description=payload.description,
        start_dt_utc=payload.start_dt_utc,
        end_dt_utc=payload.end_dt_utc,
        location=payload.location,
        calendar_id=payload.calendar_id,
    )
    if evt is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google credentials not connected")
    return evt


@router.patch("/google/events/{event_id}")
def google_update_event(event_id: str, payload: GoogleEventUpdate, db: Session = Depends(get_db), _u=Depends(require_role(1))):
    CacheRepository(db).invalidate_pattern(f"google_sync_user_id:{_u.id}")
    patch = {}
    if payload.summary is not None:
        patch["summary"] = payload.summary
    if payload.description is not None:
        patch["description"] = payload.description
    if payload.start_dt_utc is not None or payload.end_dt_utc is not None:
        if payload.start_dt_utc is not None:
            patch.setdefault("start", {})["dateTime"] = payload.start_dt_utc.isoformat()
            patch["start"]["timeZone"] = "UTC"
        if payload.end_dt_utc is not None:
            patch.setdefault("end", {})["dateTime"] = payload.end_dt_utc.isoformat()
            patch["end"]["timeZone"] = "UTC"
    evt = update_event(db=db, user_id=_u.id, event_id=event_id, patch=patch, calendar_id=payload.calendar_id)
    if evt is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google credentials not connected or update failed")
    return evt


@router.delete("/google/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def google_delete_event(event_id: str, db: Session = Depends(get_db), _u=Depends(require_role(1)), calendar_id: Optional[str] = Query(None)):
    CacheRepository(db).invalidate_pattern(f"google_sync_user_id:{_u.id}")
    ok = delete_event(db=db, user_id=_u.id, event_id=event_id, calendar_id=calendar_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google credentials not connected or delete failed")
    return

