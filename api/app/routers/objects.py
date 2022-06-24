from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import events as events_repository
from app.repositories import objects as objects_repository
from app.schemas import object as object_schemas
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/objects/", response_model=list[object_schemas.Object])
def get_objects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:read"]
    ),
):
    return objects_repository.get_objects(db, skip=skip, limit=limit)


@router.get("/objects/{object_id}", response_model=object_schemas.Object)
def get_object_by_id(
    object_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:read"]
    ),
):
    db_object = objects_repository.get_object_by_id(db, object_id=object_id)
    if db_object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
        )
    return db_object


@router.post(
    "/objects/",
    response_model=object_schemas.Object,
    status_code=status.HTTP_201_CREATED,
)
def create_object(
    object: object_schemas.ObjectCreate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:create"]
    ),
):
    event = events_repository.get_event_by_id(db, event_id=object.event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    return objects_repository.create_object(db=db, object=object)


@router.patch("/objects/{object_id}", response_model=object_schemas.Object)
def update_object(
    object_id: int,
    object: object_schemas.ObjectUpdate,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:update"]
    ),
):
    return objects_repository.update_object(db=db, object_id=object_id, object=object)


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["objects:delete"]
    ),
):
    return objects_repository.delete_object(db=db, object_id=object_id)
