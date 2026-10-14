"""Inbound alert webhooks: managed with alert_receivers:* scopes, posted to
by SIEMs and SOARs at /webhooks/alerts/{token} (see
``app.repositories.alert_receivers``)."""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.db.session import get_db
from app.repositories import alert_receivers as receivers_repository
from app.repositories import sightings as sightings_repository
from app.schemas import alert_receiver as receiver_schemas
from app.schemas import user as user_schemas
from app.services import audit

router = APIRouter()

READ = ["alert_receivers:read"]
# A receiver reports sightings for its organisation: managing one takes the
# right to report them.
MANAGE = ["alert_receivers:read", "alert_receivers:manage", "sightings:create"]


class RedactTokens(logging.Filter):
    """Keeps tokens out of access logs: the URL is the credential."""

    PATTERN = re.compile(r"/webhooks/alerts/[^\s?\"/]+")
    REPLACEMENT = "/webhooks/alerts/<token>"

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.PATTERN.sub(self.REPLACEMENT, record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                self.PATTERN.sub(self.REPLACEMENT, a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(RedactTokens())


def _get(db: Session, user, receiver_id: int):
    try:
        return receivers_repository.get_receiver(db, user, receiver_id)
    except receivers_repository.ReceiverNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert receiver not found")


def _audit(db, request, user, action: str, receiver, **metadata) -> None:
    audit.record(
        db,
        action=action,
        resource_type="alert_receiver",
        resource_id=receiver.id,
        actor_user_id=user.id,
        request=request,
        metadata={"name": receiver.name, **metadata},
    )


def _created(receiver, token: str) -> dict:
    return {
        **receiver_schemas.AlertReceiver.model_validate(receiver).model_dump(),
        "token": token,
        "path": receivers_repository.path_of(token),
    }


@router.get(
    "/alert-receivers/presets", response_model=list[receiver_schemas.AlertPreset]
)
def list_presets(
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """The senders with a ready mapping, how to set each up, and a body as
    each posts it."""
    return receivers_repository.presets()


@router.post("/alert-receivers/test", response_model=receiver_schemas.MappingResult)
def test_mapping(
    data: receiver_schemas.MappingTest,
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """What a body would report with a mapping. Nothing is written."""
    return receivers_repository.try_mapping(data, data.name)


@router.get("/alert-receivers", response_model=list[receiver_schemas.AlertReceiver])
def list_receivers(
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    """Your organisation's receivers (every organisation's, for admins)."""
    return receivers_repository.visible(db, user)


@router.post(
    "/alert-receivers",
    response_model=receiver_schemas.AlertReceiverCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_receiver(
    data: receiver_schemas.AlertReceiverCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """A new receiver. Its token is in this response only."""
    try:
        receiver, token = receivers_repository.create_receiver(db, data, user)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Your organisation has an alert receiver {data.name!r}",
        )
    _audit(db, request, user, "alert_receiver.created", receiver)
    db.commit()
    return _created(receiver, token)


@router.get(
    "/alert-receivers/{receiver_id}", response_model=receiver_schemas.AlertReceiver
)
def get_receiver(
    receiver_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=READ),
):
    return _get(db, user, receiver_id)


@router.patch(
    "/alert-receivers/{receiver_id}", response_model=receiver_schemas.AlertReceiver
)
def update_receiver(
    receiver_id: int,
    data: receiver_schemas.AlertReceiverUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    receiver = _get(db, user, receiver_id)
    try:
        receiver = receivers_repository.update_receiver(db, receiver, data)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Your organisation has an alert receiver {data.name!r}",
        )
    _audit(
        db,
        request,
        user,
        "alert_receiver.updated",
        receiver,
        fields=sorted(data.model_dump(exclude_unset=True)),
    )
    db.commit()
    return receiver


@router.delete("/alert-receivers/{receiver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receiver(
    receiver_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    receiver = _get(db, user, receiver_id)
    _audit(db, request, user, "alert_receiver.deleted", receiver)
    receivers_repository.delete_receiver(db, receiver)


@router.post(
    "/alert-receivers/{receiver_id}/token",
    response_model=receiver_schemas.AlertReceiverCreated,
)
def rotate_token(
    receiver_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """A new token; the old one stops working now. In this response only."""
    receiver = _get(db, user, receiver_id)
    previous = receiver.token_prefix
    token = receivers_repository.rotate_token(db, receiver)
    _audit(
        db,
        request,
        user,
        "alert_receiver.token_rotated",
        receiver,
        previous=previous,
        token=receiver.token_prefix,
    )
    db.commit()
    return _created(receiver, token)


@router.get(
    "/alert-receivers/{receiver_id}/last-payload",
    response_model=receiver_schemas.LastPayload,
)
def last_payload(
    receiver_id: int,
    db: Session = Depends(get_db),
    user: user_schemas.User = Security(get_current_active_user, scopes=MANAGE),
):
    """The last body posted, to try the mapping on. Alerts can carry more
    than indicators, so only those managing the receiver read it."""
    receiver = _get(db, user, receiver_id)
    return {
        "received_at": receiver.last_received_at,
        "payload": receiver.last_payload,
    }


# ── What senders post ─────────────────────────────────────────────────────


@router.post(
    "/webhooks/alerts/{token}",
    response_model=receiver_schemas.AlertAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"description": "The body is no JSON"},
        403: {"description": "The receiver is disabled, or not from this address"},
        404: {"description": "No such token"},
        413: {"description": "The body, or the sightings in it, are too many"},
        422: {"description": "The mapping can't read the body"},
        429: {"description": "Past the receiver's rate limit"},
    },
)
async def receive_alert(token: str, request: Request, db: Session = Depends(get_db)):
    """Report the values an alert hit as sightings, read from the body with
    the receiver's mapping. The token in the URL is the only credential:
    senders' webhooks seldom send an Authorization header. All or nothing:
    a body refused reports none of its sightings."""
    receiver = await run_in_threadpool(receivers_repository.find_by_token, db, token)
    if receiver is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    # The address the connection came from: uvicorn's --forwarded-allow-ips
    # decides whether a proxy's X-Forwarded-For counts, never the client.
    ip = request.client.host if request.client else None
    reason = receivers_repository.refused(receiver, ip)
    if reason == "disabled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This receiver is disabled")
    if reason == "address":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not from this address")
    retry_after = await run_in_threadpool(receivers_repository.rate_limited, receiver)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"At most {receiver.rate_limit} requests a minute",
            headers={"Retry-After": str(retry_after)},
        )

    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > receivers_repository.MAX_BODY:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Body too large")
    body = b""
    async for chunk in request.stream():
        body += chunk
        if len(body) > receivers_repository.MAX_BODY:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Body too large"
            )

    # Mapping and indexing block: off the event loop.
    return await run_in_threadpool(_report, db, receiver, body, ip)


def _report(db: Session, receiver, body: bytes, ip) -> dict:
    receivers_repository.received(db, receiver, body, ip)
    try:
        payload = receivers_repository.parse_body(body)
    except receivers_repository.MappingError as error:
        receivers_repository.failed(db, receiver, str(error))
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    try:
        result = receivers_repository.receive(db, receiver, payload)
    except receivers_repository.MappingError as error:
        receivers_repository.failed(db, receiver, str(error))
        db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error))
    except sightings_repository.TooManySightings as error:
        receivers_repository.failed(db, receiver, str(error))
        db.commit()
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(error))
    db.commit()
    return result
