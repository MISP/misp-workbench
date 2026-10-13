"""Detection profiles shared by all outputs (see ``app.repositories.detection_profiles``)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import detection_profiles as profiles_repository
from app.schemas import detection_profile as profile_schemas
from app.schemas import user as user_schemas
from app.services import audit

router = APIRouter()


def _get_or_404(db: Session, profile_id: int):
    profile = profiles_repository.get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Detection profile not found")
    return profile


def _audit(db, request, user, action, profile):
    audit.record(
        db,
        action=action,
        resource_type="detection_profile",
        resource_id=profile.id,
        actor_user_id=user.id,
        request=request,
        metadata={"name": profile.name},
    )
    db.commit()


@router.get(
    "/detection-profiles", response_model=list[profile_schemas.DetectionProfile]
)
def list_profiles(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    return profiles_repository.get_profiles(db)


@router.post(
    "/detection-profiles/preview", response_model=profile_schemas.ProfilePreview
)
async def preview_rules(
    request: profile_schemas.ProfilePreviewRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    """How many indicators these rules select, before saving them."""
    return await run_in_threadpool(profiles_repository.preview, request.rules)


@router.post("/detection-profiles/query", response_model=profile_schemas.ProfileQuery)
async def rules_as_query(
    request: profile_schemas.ProfilePreviewRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    """These rules as a Lucene query on the indicators index, for Explore."""
    return await run_in_threadpool(
        profiles_repository.to_lucene, request.rules, profiles_repository.context()
    )


@router.get(
    "/detection-profiles/{profile_id}/query",
    response_model=profile_schemas.ProfileQuery,
)
async def profile_as_query(
    profile_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    """The profile as a Lucene query on the indicators index, for Explore."""
    profile = _get_or_404(db, profile_id)
    return await run_in_threadpool(
        profiles_repository.to_lucene, profile.rules, profiles_repository.context()
    )


@router.get(
    "/detection-profiles/{profile_id}", response_model=profile_schemas.DetectionProfile
)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    return _get_or_404(db, profile_id)


@router.get(
    "/detection-profiles/{profile_id}/count",
    response_model=profile_schemas.ProfilePreview,
)
async def count_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    profile = _get_or_404(db, profile_id)
    return await run_in_threadpool(profiles_repository.preview, profile.rules)


@router.post(
    "/detection-profiles",
    response_model=profile_schemas.DetectionProfile,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    profile: profile_schemas.DetectionProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:create"]
    ),
):
    try:
        created = profiles_repository.create_profile(db, profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A profile named {profile.name!r} exists"
        )
    _audit(db, request, user, "detection_profile.created", created)
    return created


@router.patch(
    "/detection-profiles/{profile_id}",
    response_model=profile_schemas.DetectionProfile,
)
def update_profile(
    profile_id: int,
    profile: profile_schemas.DetectionProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:update"]
    ),
):
    db_profile = _get_or_404(db, profile_id)
    try:
        updated = profiles_repository.update_profile(db, db_profile, profile)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A profile named {profile.name!r} exists"
        )
    _audit(db, request, user, "detection_profile.updated", updated)
    return updated


@router.delete(
    "/detection-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_profile(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:delete"]
    ),
):
    db_profile = _get_or_404(db, profile_id)
    try:
        profiles_repository.delete_profile(db, db_profile)
    except profiles_repository.ProfileInUse as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Still used by {error}; point them elsewhere first",
        )
    _audit(db, request, user, "detection_profile.deleted", db_profile)
