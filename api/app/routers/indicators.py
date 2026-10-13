"""Consolidated indicators: one record per type + value (see ``app.repositories.indicators``)."""

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from fastapi.concurrency import run_in_threadpool

from app.auth.security import get_current_active_user
from app.repositories import indicators as indicators_repository
from app.repositories import source_quality as source_quality_repository
from app.repositories import stream_exports as stream_exports_repository
from app.schemas import indicator as indicator_schemas
from app.schemas import user as user_schemas
from app.services.runtime_settings import RuntimeSettings
from app.services.runtime_settings_provider import get_runtime_settings

router = APIRouter()


def _load_profile(ref):
    from app.repositories import detection_profiles

    if ref in (None, ""):
        return None
    try:
        return detection_profiles.load(ref)
    except detection_profiles.ProfileNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("/indicators", response_model=indicator_schemas.IndicatorPage)
async def search_indicators(
    q: Optional[str] = Query(
        None, description="Lucene query; bare terms match the value"
    ),
    type: Optional[str] = Query(None),
    to_ids: Optional[bool] = Query(None),
    include_deleted: bool = Query(
        False, description="Include tombstones of removed indicators"
    ),
    sort: Literal["score", "last_seen", "first_seen", "event_count", "updated_at"] = (
        Query("last_seen")
    ),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    profile: Optional[str] = Query(
        None, description="Only indicators a detection profile (id or name) selects"
    ),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    try:
        return await run_in_threadpool(
            indicators_repository.search,
            q,
            type,
            to_ids,
            include_deleted,
            sort,
            page,
            size,
            min_score,
            await run_in_threadpool(_load_profile, profile),
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.get("/indicators/export")
async def export_indicators(
    request: Request,
    query: str = Query("", min_length=0),
    format: Optional[str] = Query("json"),
    since: Optional[str] = Query(
        None,
        description=(
            "Only indicators that changed since this time (epoch seconds, ISO date "
            "or relative age like 7d), removed ones included as tombstones. "
            "Use the X-Export-Timestamp header of the previous export."
        ),
    ),
    include_deleted: bool = Query(False),
    enforce_warninglist: Optional[bool] = Query(
        None,
        description=(
            "Leave out indicators on an enabled warninglist (full exports only). "
            "Defaults to the warninglists.enforce_on_outputs runtime setting."
        ),
    ),
    profile: Optional[str] = Query(
        None,
        description=(
            "A detection profile (id or name) selecting what is exported, "
            "instead of include_deleted and enforce_warninglist"
        ),
    ),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """Every indicator matching ``query``, streamed (formats as /attributes/export)."""
    loaded = await run_in_threadpool(_load_profile, profile)
    if enforce_warninglist is None:
        enforce_warninglist = bool(
            await run_in_threadpool(
                runtime_settings.get_value, "warninglists.enforce_on_outputs", True
            )
        )
    try:
        export = await run_in_threadpool(
            stream_exports_repository.prepare_attribute_export,
            query,
            format,
            since,
            include_deleted,
            enforce_warninglist,
            stream_exports_repository.INDICATORS_INDEX,
            loaded,
        )
    except stream_exports_repository.RestSearchError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    max_concurrent = await run_in_threadpool(
        runtime_settings.get_value, "exports.max_concurrent_per_user", 3
    )
    return await stream_exports_repository.to_response(
        export, request, user_id=user.id, max_concurrent=max_concurrent
    )


@router.post("/indicators/scores", response_model=indicator_schemas.ScoresResponse)
async def indicator_scores(
    request: indicator_schemas.ScoresRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """The score of the indicator behind each attribute (type + value), in order."""
    scores = await run_in_threadpool(
        indicators_repository.scores_for,
        [(a.type, a.value) for a in request.attributes],
    )
    return {"scores": scores}


@router.get("/indicators/status", response_model=indicator_schemas.IndicatorsStatus)
async def indicators_status(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return await run_in_threadpool(indicators_repository.status)


@router.get("/indicators/sources", response_model=indicator_schemas.SourceQualityReport)
async def source_quality_report(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """Volume, overlap, hit rate, false-positive rate and trust of every source."""
    return await run_in_threadpool(source_quality_repository.statistics)


@router.get(
    "/indicators/sources/{kind}/{key}",
    response_model=indicator_schemas.SourceQuality,
)
async def source_quality(
    kind: Literal["feed", "server", "organisation", "local", "unknown"],
    key: str,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """One source's quality: /indicators/sources/feed/3, .../organisation/5, .../local/-"""
    if kind == "organisation":
        if not key.isdigit():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organisation not found")
        only = ("organisation", int(key))
    elif kind in ("feed", "server"):
        if not key.isdigit():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
        only = ("source", f"{kind}:{int(key)}")
    else:
        only = ("source", kind)
    report = await run_in_threadpool(source_quality_repository.statistics, None, only)
    found = report["sources"] + report["organisations"]
    if not found:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No indicators from this source yet"
        )
    return found[0]


@router.get("/indicators/{indicator_uuid}", response_model=indicator_schemas.Indicator)
async def get_indicator(
    indicator_uuid: UUID,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    indicator = await run_in_threadpool(
        indicators_repository.get_indicator, str(indicator_uuid)
    )
    if indicator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found"
        )
    return indicator
