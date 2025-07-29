from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import notifications as notifications_repository
from app.schemas import user as user_schemas
from fastapi import (
    APIRouter,
    Depends,
    Security,
)
from sqlalchemy.orm import Session

router = APIRouter()


@router.get(
    "/notifications/followers/organisation/{organisation_uuid}",
    response_model=list[user_schemas.User],
)
async def get_users_following_organisation(
    organisation_uuid: str,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=["notifications:admin    "]),
) -> list[user_schemas.User]:
    return notifications_repository.get_followers_for_organisation(
        db, organisation_uuid=organisation_uuid
    )
