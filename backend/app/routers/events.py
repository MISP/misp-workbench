from ..schemas import event as event_schemas
from ..repositories import events as events_repository
from ..dependencies import get_db
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


async def get_events_parameters(
        skip: int = 0,
        limit: int = 100,
        id: Optional[int] = None,
        info: Optional[str] = None):

    return {
        "skip": skip,
        "limit": limit,
        "filters": {
            "id":  id,
            "info": info
        }
    }


@router.get("/events/", response_model=list[event_schemas.Event])
async def get_events(params: dict = Depends(get_events_parameters), db: Session = Depends(get_db)):
    return events_repository.get_events(
        db,
        params["skip"],
        params["limit"],
        params["filters"]
    )


@router.get("/events/{event_id}", response_model=event_schemas.Event)
def get_event_by_id(event_id: int, db: Session = Depends(get_db)):
    db_event = events_repository.get_event_by_id(db, event_id=event_id)
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


@router.post("/events/", response_model=event_schemas.Event)
def create_event(event: event_schemas.EventCreate, db: Session = Depends(get_db)):
    return events_repository.create_event(db=db, event=event)
