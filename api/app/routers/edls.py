"""External dynamic lists: managed with edls:* scopes, fetched by firewalls
at /edl/{token} (see ``app.repositories.edls``)."""

import logging
import re
from email.utils import format_datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import edls as edls_repository
from app.routers.exports import _not_modified, _open_artifact
from app.schemas import edl as edl_schemas
from app.schemas import user as user_schemas
from app.services import audit
from app.worker import tasks

router = APIRouter()

READ = ["edls:read"]
MANAGE = ["edls:read", "edls:manage"]
ACTOR_EDL_TOKEN = "edl_token"


class RedactTokens(logging.Filter):
    """Keeps tokens out of access logs: the URL is the credential."""

    PATTERN = re.compile(r"/edl/[^\s?\"/]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.PATTERN.sub("/edl/<token>", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                self.PATTERN.sub("/edl/<token>", a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(RedactTokens())


def _get(db: Session, user, edl_id: int):
    try:
        return edls_repository.get_edl(db, user, edl_id)
    except edls_repository.EdlNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "EDL not found")


def _audit(db, request, user, action: str, edl, **metadata) -> None:
    audit.record(
        db,
        action=action,
        resource_type="edl",
        resource_id=edl.id,
        actor_user_id=user.id,
        request=request,
        metadata={"name": edl.name, **metadata},
    )


def _out(db: Session, edls: list) -> list[dict]:
    counts = edls_repository.active_tokens(db, [e.id for e in edls])
    return [
        {
            **edl_schemas.Edl.model_validate(e).model_dump(),
            "active_tokens": counts.get(e.id, 0),
        }
        for e in edls
    ]


@router.get("/edls/vendors", response_model=list[edl_schemas.VendorInfo])
def list_vendors(
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """The vendors lists can be written for, the lists each takes and its
    size limit by default."""
    return edls_repository.vendors()


@router.get("/edls", response_model=list[edl_schemas.Edl])
def list_edls(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """Your organisation's lists (every organisation's, for admins)."""
    return _out(db, edls_repository.visible(db, user))


@router.post(
    "/edls", response_model=edl_schemas.Edl, status_code=status.HTTP_201_CREATED
)
def create_edl(
    data: edl_schemas.EdlCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    try:
        edl = edls_repository.create_edl(db, data, user)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Your organisation has an EDL {data.name!r}"
        )
    _audit(db, request, user, "edl.created", edl)
    db.commit()
    tasks.build_edl.delay(edl.id)
    return _out(db, [edl])[0]


@router.get("/edls/{edl_id}", response_model=edl_schemas.Edl)
def get_edl(
    edl_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    return _out(db, [_get(db, user, edl_id)])[0]


@router.patch("/edls/{edl_id}", response_model=edl_schemas.Edl)
def update_edl(
    edl_id: int,
    data: edl_schemas.EdlUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    edl = _get(db, user, edl_id)
    try:
        edl = edls_repository.update_edl(db, edl, data)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Your organisation has an EDL {data.name!r}"
        )
    _audit(db, request, user, "edl.updated", edl)
    db.commit()
    tasks.build_edl.delay(edl.id)
    return _out(db, [edl])[0]


@router.delete("/edls/{edl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edl(
    edl_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    edl = _get(db, user, edl_id)
    _audit(db, request, user, "edl.deleted", edl)
    edls_repository.delete_edl(db, edl)


@router.post("/edls/{edl_id}/build", response_model=edl_schemas.Edl)
def build_edl(
    edl_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """Rebuild the list now, rather than at its next refresh."""
    edl = _get(db, user, edl_id)
    edls_repository.build(db, edl)
    db.refresh(edl)
    return _out(db, [edl])[0]


@router.get("/edls/{edl_id}/preview", response_model=edl_schemas.EdlPreview)
async def preview_edl(
    edl_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """The first lines of the list, as firewalls get it."""
    edl = _get(db, user, edl_id)
    return await run_in_threadpool(edls_repository.preview, edl)


@router.get("/edls/{edl_id}/tokens", response_model=list[edl_schemas.EdlToken])
def list_tokens(
    edl_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    return edls_repository.tokens_of(db, _get(db, user, edl_id))


@router.post(
    "/edls/{edl_id}/tokens",
    response_model=edl_schemas.EdlTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_token(
    edl_id: int,
    data: edl_schemas.EdlTokenCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """A token for this list only. Its value is in this response and
    nowhere else: only its hash is kept."""
    edl = _get(db, user, edl_id)
    token, value = edls_repository.create_token(db, edl, data, user)
    _audit(
        db,
        request,
        user,
        "edl.token_created",
        edl,
        token=token.prefix,
        allowed_ips=token.allowed_ips,
    )
    db.commit()
    db.refresh(token)
    return {
        **edl_schemas.EdlToken.model_validate(token).model_dump(),
        "token": value,
        "path": f"/edl/{value}",
    }


@router.delete(
    "/edls/{edl_id}/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revoke_token(
    edl_id: int,
    token_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """Revoke a token: the list stops answering it at once."""
    edl = _get(db, user, edl_id)
    try:
        token = edls_repository.get_token(db, edl, token_id)
    except edls_repository.EdlNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    edls_repository.revoke_token(db, token)
    _audit(db, request, user, "edl.token_revoked", edl, token=token.prefix)
    db.commit()


# ── What firewalls fetch ──────────────────────────────────────────────────


@router.get(
    "/edl/{token}",
    response_class=Response,
    responses={
        200: {"content": {"text/plain": {}}, "description": "The list"},
        304: {"description": "Unchanged since the ETag sent"},
        403: {"description": "The token can't be used from this address"},
        404: {"description": "No such token, or revoked or expired"},
        503: {"description": "The list hasn't been built yet"},
    },
)
async def fetch_edl(token: str, request: Request, db: Session = Depends(get_db)):
    """The list a token is for, one entry per line. The token in the URL is
    the only credential: firewalls can't send an Authorization header."""
    row = edls_repository.find_token(db, token)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    edl = db.get(edls_repository.edl_models.Edl, row.edl_id)
    # The address the connection came from: uvicorn's --forwarded-allow-ips
    # decides whether a proxy's X-Forwarded-For counts, never the client.
    ip = request.client.host if request.client else None
    reason = edls_repository.refused(row, ip)

    def record(action: str, **metadata) -> None:
        audit.record(
            db,
            action=action,
            resource_type="edl",
            resource_id=edl.id,
            actor_type=ACTOR_EDL_TOKEN,
            actor_credential_id=row.id,
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
            metadata={"name": edl.name, "token": row.prefix, **metadata},
        )

    if reason is not None:
        record("edl.fetch_refused", reason=reason)
        db.commit()
        if reason == "address":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not from this address")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    edls_repository.record_use(row, ip)
    if not edl.enabled or not edl.storage_key or not edl.checksum:
        record("edl.fetched", status=503)
        db.commit()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The list hasn't been built yet",
            headers={"Retry-After": "60"},
        )
    headers = {"ETag": f'"{edl.checksum}"', "Cache-Control": "no-cache"}
    if edl.built_at:
        headers["Last-Modified"] = format_datetime(
            edls_repository._aware(edl.built_at), usegmt=True
        )
    if _not_modified(request, headers):
        record("edl.fetched", status=304)
        db.commit()
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    record("edl.fetched", status=200, entries=edl.entry_count)
    db.commit()
    chunks = await _open_artifact(edl.storage_key)
    return StreamingResponse(
        chunks, media_type="text/plain; charset=utf-8", headers=headers
    )
