from app.auth.auth import get_current_active_user
from app.dependencies import get_db
from app.repositories import attachments as attachments_repository
from app.schemas import user as user_schemas
from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attachments:download"]
    ),
):
    return attachments_repository.download_attachment(
        db, attachment_id=attachment_id
    )
