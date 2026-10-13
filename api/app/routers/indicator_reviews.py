"""The review queue (see ``app.repositories.indicator_reviews``)."""

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import indicator_reviews as reviews_repository
from app.schemas import indicator_review as review_schemas
from app.schemas import user as user_schemas

router = APIRouter()


@router.get("/indicators/review", response_model=review_schemas.ReviewQueuePage)
def review_queue(
    profile_id: Optional[int] = Query(
        None, description="Only indicators pending for this profile"
    ),
    q: Optional[str] = Query(
        None, description="Lucene query; bare terms match the value"
    ),
    type: Optional[str] = None,
    source: Optional[str] = Query(
        None, description="A source key: feed:3, server:2, local, unknown"
    ),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    sort: Literal["score", "last_seen", "first_seen", "event_count"] = "score",
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """Pending indicators: ones a profile requiring approval would select,
    not yet approved, rejected or snoozed."""
    try:
        return reviews_repository.queue(
            db,
            profile_id=profile_id,
            query=q,
            type_=type,
            source=source,
            min_score=min_score,
            max_score=max_score,
            sort=sort,
            page=page,
            size=size,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/indicators/review/summary", response_model=review_schemas.ReviewSummary)
def review_summary(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return reviews_repository.summary(db)


@router.get(
    "/indicators/review/decisions", response_model=review_schemas.ReviewDecisionPage
)
def review_decisions(
    status_: review_schemas.DecidedStatus = Query(..., alias="status"),
    q: Optional[str] = Query(None, description="Part of the value"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """Decided indicators, newest decision first."""
    return reviews_repository.decisions(db, status_, query=q, page=page, size=size)


@router.post(
    "/indicators/review/decisions",
    response_model=review_schemas.ReviewDecisionResult,
)
def decide(
    decision: review_schemas.ReviewDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["indicators:review"]
    ),
):
    """Approve, reject, snooze or reopen indicators (up to 500 at a time)."""
    try:
        return reviews_repository.decide(
            db,
            decision.indicators,
            decision.action,
            user_id=user.id,
            reason=decision.reason,
            snooze_days=decision.snooze_days,
            allowlist=decision.allowlist,
            request=request,
        )
    except reviews_repository.UnknownIndicators as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No indicators {', '.join(error.ids[:10])}",
        )


@router.get(
    "/indicators/{indicator_uuid}/review",
    response_model=review_schemas.IndicatorReviewDetail,
)
def indicator_review(
    indicator_uuid: UUID,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """The decision on an indicator and every decision taken before."""
    return {
        "decision": reviews_repository.get_decision(db, str(indicator_uuid)),
        "history": reviews_repository.history(db, str(indicator_uuid)),
    }
