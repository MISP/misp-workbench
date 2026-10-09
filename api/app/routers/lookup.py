"""Bulk indicator lookup for SIEM enrichment (see ``app.repositories.lookup``)."""

from fastapi import APIRouter, HTTPException, Query, Security, status
from fastapi.concurrency import run_in_threadpool

from app.auth.security import get_current_active_user
from app.repositories import lookup as lookup_repository
from app.schemas import lookup as lookup_schemas
from app.schemas import user as user_schemas

router = APIRouter()


@router.post("/lookup", response_model=lookup_schemas.LookupResponse)
async def bulk_lookup(
    request: lookup_schemas.LookupRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """Which of these values are known indicators, with their context."""
    try:
        return await run_in_threadpool(
            lookup_repository.lookup,
            request.values,
            request.to_ids_only,
            request.max_attributes,
            request.include_warninglisted,
        )
    except lookup_repository.TooManyValues as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)
        )


@router.get("/lookup", response_model=lookup_schemas.SingleLookupResponse)
async def single_lookup(
    value: str = Query(..., min_length=1),
    to_ids_only: bool = Query(True),
    max_attributes: int = Query(10, ge=1, le=100),
    include_warninglisted: bool = Query(False),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    """One value per request, for per-key lookup adapters (e.g. Graylog's HTTP JSONPath)."""
    result = await run_in_threadpool(
        lookup_repository.lookup,
        [value],
        to_ids_only,
        max_attributes,
        include_warninglisted,
    )
    if not result["matches"]:
        return lookup_schemas.SingleLookupResponse(value=value, match=False)
    match = result["matches"][0]
    return lookup_schemas.SingleLookupResponse(
        value=value,
        match=True,
        attribute_count=match["attribute_count"],
        attributes=match["attributes"],
    )


@router.get("/lookup/cache", response_model=lookup_schemas.LookupCacheStatus)
async def lookup_cache_status(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return await run_in_threadpool(lookup_repository.cache_status)
