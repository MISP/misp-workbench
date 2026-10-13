"""Detection profiles shared by all outputs (see ``app.repositories.detection_profiles``)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import SecurityScopes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import detection_profiles as profiles_repository
from app.repositories import profile_gate
from app.schemas import detection_profile as profile_schemas
from app.schemas import user as user_schemas
from app.services import audit

router = APIRouter()


def _get_or_404(db: Session, profile_id: int):
    profile = profiles_repository.get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Detection profile not found")
    return profile


async def _can_review(request: Request, db: Session = Depends(get_db)) -> bool:
    """Whether the caller (its token or API key) holds indicators:review."""
    try:
        await get_current_active_user(
            SecurityScopes(["indicators:review"]), request, None, db
        )
    except HTTPException:
        return False
    return True


def _weakens_review(before, patch: dict) -> Optional[str]:
    """What, in a create (``before`` None) or an update, decides what goes
    out without a review: those are for reviewers (indicators:review), not
    only for whoever edits profiles."""

    def rules(raw):
        return profiles_repository._rules(raw).model_dump()

    def gate(raw):
        return profile_gate.gate_of(raw).model_dump()

    old_rules = rules(before.rules) if before is not None else rules({})
    old_auto = bool(before.auto_approve) if before is not None else False
    new_rules = rules(patch["rules"]) if "rules" in patch else None
    new_auto = patch.get("auto_approve", old_auto)
    if "gate" in patch and gate(patch["gate"]) != gate(before.gate if before else None):
        return "its approval gate"
    if new_auto != old_auto and new_auto:
        return "auto-approval"
    if new_auto and new_rules is not None and new_rules != old_rules:
        return "the rules of an auto-approve profile"
    if new_rules is not None and before is not None:
        for rule in ("require_approval", "exclude_rejected"):
            if old_rules.get(rule) and not new_rules.get(rule):
                return f"turning {rule.replace('_', ' ')} off"
    return None


def _your_lists(db: Session, user) -> dict:
    """The viewer's organisation's lists (id -> name), to flag additions on."""
    from app.repositories import local_warninglists

    return {w.id: w.name for w in local_warninglists.visible(db, user)}


def _check_lists(db: Session, user, patch: dict, before=None) -> None:
    """A profile attaches organisations' lists its editor can see (ones
    attached already, by someone else, can stay)."""
    from app.repositories import local_warninglists

    attached = set(
        ((before.rules or {}) if before is not None else {}).get("exclude_lists") or []
    )
    wanted = set((patch.get("rules") or {}).get("exclude_lists") or []) - attached
    unknown = wanted - local_warninglists.visible_ids(db, user)
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"No organisation warninglist {', '.join(map(str, sorted(unknown)))}",
        )


def _check_review(before, patch: dict, can_review: bool) -> None:
    what = _weakens_review(before, patch)
    if what and not can_review:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Changing {what} needs the indicators:review scope",
        )


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
    profiles = profiles_repository.get_profiles(db)
    held = profile_gate.held_profiles(db)
    for profile in profiles:
        profile.held = profile.id in held
    return profiles


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
    profile = _get_or_404(db, profile_id)
    profile.held = profile.id in profile_gate.held_profiles(db)
    return profile


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
    can_review: bool = Depends(_can_review),
):
    _check_review(None, profile.model_dump(exclude_unset=True), can_review)
    _check_lists(db, user, profile.model_dump(exclude_unset=True))
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
    can_review: bool = Depends(_can_review),
):
    db_profile = _get_or_404(db, profile_id)
    _check_review(db_profile, profile.model_dump(exclude_unset=True), can_review)
    _check_lists(db, user, profile.model_dump(exclude_unset=True), db_profile)
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


@router.get(
    "/detection-profiles/{profile_id}/changes",
    response_model=profile_schemas.ChangePreview,
)
def preview_changes(
    profile_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    """What the profile's next run changes against its last release, whether
    the gate would hold it, and the recent runs."""
    _get_or_404(db, profile_id)
    return profile_gate.preview(db, profile_id, your_lists=_your_lists(db, user))


@router.post(
    "/detection-profiles/{profile_id}/changes",
    response_model=profile_schemas.ChangePreview,
)
def dry_run_changes(
    profile_id: int,
    request: profile_schemas.ChangePreviewRequest,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["detection_profiles:read"]
    ),
):
    """The same, for rules not saved yet: what saving them would change."""
    _get_or_404(db, profile_id)
    return profile_gate.preview(
        db, profile_id, rules=request.rules, your_lists=_your_lists(db, user)
    )


@router.post(
    "/detection-profiles/{profile_id}/changes/approve",
    response_model=profile_schemas.ProfileRelease,
)
def approve_changes(
    profile_id: int,
    approval: profile_schemas.ApproveChangesRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["indicators:review"]
    ),
):
    """Release the previewed changes (named by their fingerprint), and run
    the outputs that waited for them. 409 when they moved since."""
    profile = _get_or_404(db, profile_id)
    try:
        released = profile_gate.approve(db, profile_id, user.id, approval.fingerprint)
    except (profile_gate.GateBusy, profile_gate.ChangesMoved) as conflict:
        raise HTTPException(status.HTTP_409_CONFLICT, str(conflict))
    audit.record(
        db,
        action="detection_profile.changes_approved",
        resource_type="detection_profile",
        resource_id=profile.id,
        actor_user_id=user.id,
        request=request,
        metadata={
            "name": profile.name,
            "added": released["added"],
            "removed": released["removed"],
        },
    )
    db.commit()
    return next(
        r for r in profile_gate.releases(db, profile_id, 5) if r["id"] == released["id"]
    )
