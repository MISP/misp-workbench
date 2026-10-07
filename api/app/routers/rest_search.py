"""MISP-compatible restSearch endpoints.

Lets existing MISP integrations (Splunk MISP42, Wazuh, Graylog, PyMISP) query
misp-workbench unmodified. Filters are documented in
``app.repositories.rest_search``. Both GET (query string) and POST (JSON body,
MISP's usual form) are accepted.
"""

import json

from fastapi import APIRouter, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.auth.security import get_current_active_user
from app.repositories import rest_search as rest_search_repository
from app.schemas import user as user_schemas

router = APIRouter()


async def _read_params(request: Request) -> dict:
    if request.method == "GET":
        params: dict = {}
        for key in request.query_params.keys():
            values = request.query_params.getlist(key)
            params[key] = values[0] if len(values) == 1 else values
        return params

    body = await request.body()
    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="restSearch body must be valid JSON",
        )


def _bad_request(error: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


async def _attributes_response(request: Request) -> StreamingResponse:
    params = await _read_params(request)
    try:
        # Resolving event-level filters queries OpenSearch synchronously.
        search = await run_in_threadpool(
            rest_search_repository.prepare_attribute_search, params
        )
    except rest_search_repository.RestSearchError as error:
        raise _bad_request(error)

    return StreamingResponse(
        rest_search_repository.stream_attributes(search),
        media_type=search.media_type,
    )


async def _events_response(request: Request) -> StreamingResponse:
    params = await _read_params(request)
    try:
        search = await run_in_threadpool(
            rest_search_repository.prepare_event_search, params
        )
    except rest_search_repository.RestSearchError as error:
        raise _bad_request(error)

    return StreamingResponse(
        rest_search_repository.stream_events(search),
        media_type=search.media_type,
    )


@router.post("/attributes/restSearch")
async def attributes_rest_search(
    request: Request,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return await _attributes_response(request)


@router.get("/attributes/restSearch")
async def attributes_rest_search_get(
    request: Request,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["attributes:read"]
    ),
):
    return await _attributes_response(request)


@router.post("/events/restSearch")
async def events_rest_search(
    request: Request,
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
):
    return await _events_response(request)


@router.get("/events/restSearch")
async def events_rest_search_get(
    request: Request,
    user: user_schemas.User = Security(get_current_active_user, scopes=["events:read"]),
):
    return await _events_response(request)
