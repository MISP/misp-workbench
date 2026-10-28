import functools
import logging
import os
import smtplib
import time
from email.message import EmailMessage
from datetime import datetime, timezone
from uuid import UUID

from app.database import SQLALCHEMY_DATABASE_URL
from app.services.opensearch import get_opensearch_client
from app.services import ingest_runs
from app.services.redis import get_redis_client
from app.settings import get_settings
from app.services.runtime_settings_provider import get_runtime_settings
from app.repositories import events as events_repository
from app.repositories import feeds as feeds_repository
from app.repositories import freetext as freetext_repository
from app.repositories import servers as servers_repository
from app.repositories import objects as objects_repository
from app.repositories import users as users_repository
from app.repositories import correlations as correlations_repository
from app.repositories import servos as servos_repository
from app.services.tech_lab.servos import chain as servo_chain
from app.repositories import attributes as attributes_repository
from app.repositories import notifications as notifications_repository
from app.repositories import galaxies as galaxies_repository
from app.repositories import hunts as hunts_repository
from app.repositories import reactor as reactor_repository
from app.repositories import taxonomies as taxonomies_repository
from app.schemas import attribute as attribute_schemas
from app.services.tech_lab.reactor import runner as reactor_runner
from app.services.tech_lab.lab import executor as lab_executor
from app.services.tech_lab.lab import kernel_manager as lab_kernel_manager
from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Celery configuration
celery_app = Celery("misp-workbench")
celery_app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_pool_restarts=True,
    broker_transport_options={"visibility_timeout": 60 * 60 * 24},  # 24 hours,
    acks_late=False,
    worker_prefetch_multiplier=1,
    task_time_limit=None,
    task_soft_time_limit=None,
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=os.environ.get("CELERY_BROKER_URL"),
    # Every entry expires after its own interval: behind a backlog a stale run
    # is dropped, the next one is on its way, instead of the runs piling up.
    beat_schedule={
        # Keep the lookup prefilter in step with OpenSearch: add new indicator
        # values every few seconds, rebuild (dropping stale ones) hourly.
        "lookup-cache-sync": {
            "task": "app.worker.tasks.sync_lookup_cache",
            "schedule": 15.0,
            "options": {"expires": 15},
        },
        "lookup-cache-rebuild": {
            "task": "app.worker.tasks.rebuild_lookup_cache",
            "schedule": 3600.0,
            "options": {"expires": 3600},
        },
        # Consolidated indicators (one per type + value): refresh what changed
        # every few seconds, walk everything hourly.
        "indicators-sync": {
            "task": "app.worker.tasks.sync_indicators",
            "schedule": 15.0,
            "options": {"expires": 15},
        },
        "indicators-rebuild": {
            "task": "app.worker.tasks.rebuild_indicators",
            "schedule": 3600.0,
            "options": {"expires": 3600},
        },
        # Keep membership-synced sinks in step with their profiles.
        "sinks-membership-sync": {
            "task": "app.worker.tasks.sync_sink_memberships",
            "schedule": 300.0,
            "options": {"expires": 300},
        },
        # Organisations' warninglists: match the indicators written since the
        # last run.
        "local-warninglists-evaluate-recent": {
            "task": "app.worker.tasks.evaluate_recent_local_warninglists",
            "schedule": 60.0,
            "options": {"expires": 60},
        },
        # Organisations' warninglists: drop expired entries, sync the lists
        # whose source URL is due (daily).
        "local-warninglists-sweep": {
            "task": "app.worker.tasks.sweep_local_warninglists",
            "schedule": 300.0,
            "options": {"expires": 300},
        },
        # External dynamic lists: rebuild those due (each has its own refresh).
        "edls-refresh": {
            "task": "app.worker.tasks.refresh_edls",
            "schedule": 60.0,
            "options": {"expires": 60},
        },
        # Look ahead at gated detection profiles: hold (and notify about)
        # changes their next run would hold, before it comes.
        "profile-gates-check": {
            "task": "app.worker.tasks.check_profile_gates",
            "schedule": 300.0,
            "options": {"expires": 300},
        },
        # Flag attributes written since the last run with the warninglists
        # they hit (a full re-evaluation runs whenever the lists change).
        # Restart ingestion runs whose drain tasks were lost (a worker killed
        # mid-batch), so they don't sit on their slot until they expire.
        "ingest-runs-revive": {
            "task": "app.worker.tasks.revive_stalled_ingest_runs",
            "schedule": 300.0,
            "options": {"expires": 300},
        },
        "warninglists-evaluate-recent": {
            "task": "app.worker.tasks.evaluate_recent_warninglist_hits",
            "schedule": 60.0,
            "options": {"expires": 60},
        },
    },
)

logger = logging.getLogger(__name__)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Queues besides Celery's default one (``celery``: user-triggered work and
# everything else), each consumed by its own worker so that one kind of work
# can't hold up the others:
# - ``ingest``: feed fetches, server pulls and pushes, and the correlation
#   and notification follow-ups of bulk ingests (the ``ingest-worker``);
# - ``maintenance``: periodic jobs and rebuilds (the main ``worker``, which
#   consumes ``celery,maintenance``).
INGEST_QUEUE = "ingest"
MAINTENANCE_QUEUE = "maintenance"

# Attributes handed to a single correlate_attributes task by a bulk ingest.
CORRELATION_BATCH_SIZE = 500

# A drain task ingests ingest_runs.BATCH_SIZE events; this bounds one that hangs.
DRAIN_SOFT_TIME_LIMIT = 30 * 60
# Feeds ingested by a single task (CSV, freetext, JSON).
SINGLE_FEED_SOFT_TIME_LIMIT = 2 * 3600


def _reactor_event_payload(os_event, event_uuid: str) -> dict:
    if os_event is None:
        return {"event_uuid": event_uuid}
    data = (
        os_event.model_dump(mode="json")
        if hasattr(os_event, "model_dump")
        else dict(os_event)
    )
    data["event_uuid"] = event_uuid
    return data


def _reactor_attribute_payload(
    os_attr, attribute_uuid: str, object_uuid, event_uuid: str | None
) -> dict:
    data = (
        os_attr.model_dump(mode="json")
        if os_attr is not None and hasattr(os_attr, "model_dump")
        else (dict(os_attr) if os_attr is not None else {})
    )
    data["attribute_uuid"] = attribute_uuid
    data["object_uuid"] = object_uuid
    data["event_uuid"] = event_uuid
    return data


def _reactor_object_payload(os_obj, object_uuid: str, event_uuid: str | None) -> dict:
    data = (
        os_obj.model_dump(mode="json")
        if os_obj is not None and hasattr(os_obj, "model_dump")
        else (dict(os_obj) if os_obj is not None else {})
    )
    data["object_uuid"] = object_uuid
    data["event_uuid"] = event_uuid
    return data


def _dispatch_if_subscribed(
    resource_type: str, action: str, payload: dict, queue: str | None = None
) -> None:
    """Skip the Celery hop when no active script subscribes to this trigger.

    The gate is best-effort (Redis-backed, fail-open). If it returns False we
    can be confident no script is listening; if it returns True we still hand
    off to ``reactor_dispatch`` which does the authoritative DB check.

    ``queue``: where the dispatch goes instead of the default queue; ingest
    follow-ups pass INGEST_QUEUE, so that a large feed's thousands of
    dispatches (all of them while the gate's cache is cold) stay off it.
    """
    if not reactor_repository.has_active_subscriber(resource_type, action):
        return
    if queue:
        reactor_dispatch.apply_async((resource_type, action, payload), queue=queue)
    else:
        reactor_dispatch.delay(resource_type, action, payload)


def _ingest_settings() -> tuple[int, bool]:
    """``(max_concurrent_runs, paused)`` from the ``ingest`` runtime settings."""
    with Session(engine) as db:
        runtimeSettings = get_runtime_settings(db)
    return (
        int(runtimeSettings.get_value("ingest.max_concurrent_runs", 2) or 0),
        bool(runtimeSettings.get_value("ingest.paused", False)),
    )


def _admit_ingest_run(task, kind: str, source_id: int, user_id: int, args, queued):
    """Open (or resume waiting for) a source's ingestion run.

    Returns None when the run may go ahead, otherwise the result the task
    should return: the source is already being ingested, or the run has to
    wait for a slot (or for ingestion to be resumed) and was queued again.
    """
    if queued:
        # A retry of a run that was waiting: it may have been cancelled since.
        if not ingest_runs.is_open(kind, source_id):
            return {
                "result": "cancelled",
                "message": "%s id=%s run was cancelled." % (kind, source_id),
            }
    elif not ingest_runs.claim(kind, source_id, user_id):
        logger.info("%s id=%s already has a run, skipped", kind, source_id)
        return {
            "result": "skipped",
            "message": "%s id=%s is already queued or being ingested."
            % (kind, source_id),
        }

    max_runs, paused = _ingest_settings()
    if paused or not ingest_runs.admit(kind, source_id, max_runs):
        ingest_runs.heartbeat(kind, source_id)
        task.apply_async(
            args, {"queued": True}, countdown=ingest_runs.QUEUED_RETRY_SECONDS
        )
        return {
            "result": "queued",
            "message": "%s id=%s is waiting for %s."
            % (
                kind,
                source_id,
                "ingestion to be resumed" if paused else "an ingestion slot",
            ),
        }

    return None


def start_ingest_drainers(kind: str, source_id: int, user_id: int, count: int):
    """Queue the events of a run and the tasks that ingest them.

    Returns how many events were queued; with none, the run is closed here.
    """
    if not count:
        ingest_runs.finish(kind, source_id)
        return 0

    drainers = min(ingest_runs.DRAINERS_PER_RUN, -(-count // ingest_runs.BATCH_SIZE))
    ingest_runs.set_drainers(kind, source_id, drainers)
    for _ in range(drainers):
        drain_ingest_run.delay(kind, source_id, user_id)
    return count


def _ingest_source(db, kind: str, source_id: int):
    """The feed or server a run ingests from, None once gone or disabled."""
    if kind == "feed":
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=source_id)
        return db_feed if db_feed is not None and db_feed.enabled else None
    return servers_repository.get_server_by_id(db, source_id)


def _ingest_event(db, kind: str, event_uuid: str, source, user):
    if kind == "feed":
        feeds_repository.process_feed_event(db, event_uuid, source, user)
        return

    db_event = servers_repository.pull_event_by_uuid(
        db, event_uuid, source, user, get_settings()
    )
    if db_event:
        notifications_repository.create_event_notifications(
            db, "created", event=db_event
        )


@celery_app.task(
    queue=INGEST_QUEUE,
    soft_time_limit=DRAIN_SOFT_TIME_LIMIT,
    time_limit=DRAIN_SOFT_TIME_LIMIT + 60,
)
def drain_ingest_run(kind: str, source_id: int, user_id: int):
    """Ingest the next batch of a run's events, then queue the run's next turn.

    A failing event is logged and counted, and the batch goes on: the next
    fetch tries it again.
    """
    if not ingest_runs.is_open(kind, source_id):
        return {"result": "skipped", "message": "The run is no longer open."}

    _, paused = _ingest_settings()
    if paused:
        # Waiting, not stalled: keep the watchdog from reviving it.
        ingest_runs.record(kind, source_id, 0, 0)
        drain_ingest_run.apply_async(
            (kind, source_id, user_id), countdown=ingest_runs.QUEUED_RETRY_SECONDS
        )
        return {"result": "queued", "message": "Ingestion is paused."}

    done = failed = 0
    batch = []
    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        source = _ingest_source(db, kind, source_id)
        if user is None or source is None:
            ingest_runs.cancel(
                kind, source_id, "the %s was disabled or removed" % kind
            )
        else:
            batch = ingest_runs.take(kind, source_id)

        if batch:
            with attributes_repository.bulk_ingest():
                for index, event_uuid in enumerate(batch):
                    try:
                        _ingest_event(db, kind, event_uuid, source, user)
                        done += 1
                    except SoftTimeLimitExceeded:
                        db.rollback()
                        failed += 1
                        ingest_runs.put_back(kind, source_id, batch[index + 1 :])
                        logger.error(
                            "%s id=%s event uuid=%s hit the time limit",
                            kind,
                            source_id,
                            event_uuid,
                        )
                        break
                    except Exception:
                        db.rollback()
                        failed += 1
                        logger.exception(
                            "%s id=%s event uuid=%s failed to ingest",
                            kind,
                            source_id,
                            event_uuid,
                        )

    ingest_runs.record(kind, source_id, done, failed)

    if batch:
        drain_ingest_run.delay(kind, source_id, user_id)
    elif ingest_runs.drainer_done(kind, source_id):
        ingest_runs.finish(kind, source_id)
        logger.info("%s id=%s ingestion run finished", kind, source_id)

    return {"result": "success", "ingested": done, "failed": failed}


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def revive_stalled_ingest_runs():
    """Restart the drain tasks of runs that stopped progressing (see
    ingest_runs.stalled_runs), or close those with nothing left."""
    revived = 0
    for run in ingest_runs.stalled_runs():
        kind, source_id = run["kind"], run["source_id"]
        if run["pending"] and run["user_id"]:
            logger.warning("%s id=%s run stalled, restarting it", kind, source_id)
            ingest_runs.record(kind, source_id, 0, 0)  # restarts the clock
            start_ingest_drainers(kind, source_id, run["user_id"], run["pending"])
            revived += 1
        else:
            logger.warning("%s id=%s run stalled, closing it", kind, source_id)
            # Every event was taken, but a drain task was lost on the way.
            ingest_runs.finish(
                kind,
                source_id,
                ingest_runs.FAILED,
                "a drain task was lost; the next fetch ingests what it missed",
            )
    return revived


@celery_app.task(bind=True, queue=INGEST_QUEUE)
def server_pull_by_id(
    self, server_id: int, user_id: int, technique: str, queued: bool = False
):
    logger.info("pull server_id=%s job started", server_id)

    held = _admit_ingest_run(
        self, "server", server_id, user_id, (server_id, user_id, technique), queued
    )
    if held is not None:
        return held

    try:
        with Session(engine) as db:
            user = users_repository.get_user_by_id(db, user_id)
            if user is None:
                raise Exception("User not found")

            servers_repository.pull_server_by_id(db, server_id, user, technique)
    except Exception as error:
        ingest_runs.finish("server", server_id, ingest_runs.FAILED, str(error))
        raise

    logger.info("pull server_id=%s job finished", server_id)
    return True


# Kept for messages queued before server pulls became runs (drain_ingest_run).
@celery_app.task(queue=INGEST_QUEUE)
def pull_event_by_uuid(event_uuid: str, server_id: int, user_id: int):
    logger.info(
        "pull event uuid=%s from server id=%s, job started", event_uuid, server_id
    )

    with Session(engine) as db, attributes_repository.bulk_ingest():
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        server = servers_repository.get_server_by_id(db, server_id)
        if server is None:
            raise Exception("Server not found")

        db_event = servers_repository.pull_event_by_uuid(
            db, event_uuid, server, user, get_settings()
        )

        if db_event:
            notifications_repository.create_event_notifications(
                db, "created", event=db_event
            )

        logger.info(
            "pull event uuid=%s from server id=%s, job finished", event_uuid, server_id
        )

    return True


@celery_app.task(queue=INGEST_QUEUE)
def server_push_by_id(server_id: int, user_id: int, technique: str):
    logger.info("push server_id=%s job started", server_id)

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        servers_repository.push_server_by_id(db, server_id, user, technique)
        logger.info("push server_id=%s job finished", server_id)

    return True


@celery_app.task(queue=INGEST_QUEUE)
def push_event_by_uuid(event_uuid: str, server_id: int, user_id: int):
    logger.info(
        "push event uuid=%s to server id=%s, job started", event_uuid, server_id
    )

    with Session(engine) as db:
        user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            raise Exception("User not found")

        server = servers_repository.get_server_by_id(db, server_id)
        if server is None:
            raise Exception("Server not found")

        servers_repository.push_event_by_uuid(
            db, event_uuid, server, user, get_settings()
        )

        logger.info(
            "push event uuid=%s to server id=%s, job finished", event_uuid, server_id
        )

    return True


@celery_app.task
def handle_created_event(event_uuid: str):
    logger.info("handling created event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "created", event=os_event)
        _dispatch_if_subscribed("event", "created", _reactor_event_payload(os_event, event_uuid))

    return True


@celery_app.task
def handle_updated_event(event_uuid: str):
    logger.info("handling updated event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        get_opensearch_client().update(
            index="misp-events",
            id=event_uuid,
            body={"doc": {"timestamp": int(datetime.now().timestamp())}},
            refresh=True,
        )
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "updated", event=os_event)
        _dispatch_if_subscribed("event", "updated", _reactor_event_payload(os_event, event_uuid))

    return True


@celery_app.task
def handle_deleted_event(event_uuid: str):
    logger.info("handling deleted event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "deleted", event=os_event)
        _dispatch_if_subscribed("event", "deleted", _reactor_event_payload(os_event, event_uuid))

    # Correlations reference events on both sides, so they outlive the event
    # unless they go with it - leaving other attributes pointing at something
    # that no longer exists.
    correlations_repository.delete_event_correlations(event_uuid)

    delete_indexed_event(event_uuid)

    return True


@celery_app.task
def handle_created_attribute(
    attribute_uuid: str,
    object_uuid,
    event_uuid: str | None,
    bulk: bool = False,
):
    """Follow up on a created attribute.

    ``bulk`` marks an attribute created by an ingest, which counts and
    correlates its attributes in one pass at the end instead. See
    ``attributes_repository.bulk_ingest``.
    """
    logger.info("handling created attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        # Attributes inside objects count towards the event too, as in MISP.
        if event_uuid and not bulk:
            events_repository.increment_attribute_count(db, event_uuid)

        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "created", attribute=os_attr)
            _dispatch_if_subscribed(
                "attribute",
                "created",
                _reactor_attribute_payload(os_attr, attribute_uuid, object_uuid, event_uuid),
            )
            if not bulk:
                correlate_attribute.delay(attribute_uuid)

    return True


@celery_app.task
def handle_updated_attribute(
    attribute_uuid: str,
    object_uuid,
    event_uuid: str | None,
    recorrelate: bool = True,
):
    logger.info("handling updated attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "updated", attribute=os_attr)
            _dispatch_if_subscribed(
                "attribute",
                "updated",
                _reactor_attribute_payload(os_attr, attribute_uuid, object_uuid, event_uuid),
            )
            if recorrelate:
                correlate_attribute.delay(attribute_uuid)

    return True


@celery_app.task
def handle_deleted_attribute(attribute_uuid: str, object_uuid, event_uuid: str | None):
    logger.info("handling deleted attribute uuid=%s job started", attribute_uuid)
    with Session(engine) as db:
        if event_uuid:
            events_repository.decrement_attribute_count(db, event_uuid)

        os_attr = attributes_repository.get_attribute_from_opensearch(UUID(attribute_uuid))
        if os_attr is not None:
            notifications_repository.create_attribute_notifications(db, "deleted", attribute=os_attr)
            _dispatch_if_subscribed(
                "attribute",
                "deleted",
                _reactor_attribute_payload(os_attr, attribute_uuid, object_uuid, event_uuid),
            )

    correlations_repository.delete_attribute_correlations(attribute_uuid)

    return True


@celery_app.task
def handle_created_object(object_uuid: str, event_uuid: str | None, bulk: bool = False):
    """Follow up on a created object. ``bulk`` as in handle_created_attribute."""
    logger.info("handling created object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        if event_uuid and not bulk:
            events_repository.increment_object_count(db, event_uuid)

        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "created", object=os_obj)
            _dispatch_if_subscribed(
                "object",
                "created",
                _reactor_object_payload(os_obj, object_uuid, event_uuid),
                queue=INGEST_QUEUE if bulk else None,
            )

    return True


def enqueue_created_object(object_uuid: str, event_uuid: str | None, bulk: bool):
    """Queue handle_created_object; one per object of a bulk ingest goes to
    the ingest queue with the rest of the ingest's follow-ups."""
    if bulk:
        handle_created_object.apply_async(
            (object_uuid, event_uuid, bulk), queue=INGEST_QUEUE
        )
    else:
        handle_created_object.delay(object_uuid, event_uuid, bulk)


@celery_app.task
def handle_updated_object(object_uuid: str, event_uuid: str | None):
    logger.info("handling updated object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "updated", object=os_obj)
            _dispatch_if_subscribed(
                "object", "updated", _reactor_object_payload(os_obj, object_uuid, event_uuid)
            )

    return True


@celery_app.task
def handle_deleted_object(object_uuid: str, event_uuid: str | None):
    logger.info("handling deleted object uuid=%s job started", object_uuid)

    with Session(engine) as db:
        if event_uuid:
            events_repository.decrement_object_count(db, event_uuid)

        os_obj = objects_repository.get_object_from_opensearch(UUID(object_uuid))
        if os_obj is not None:
            notifications_repository.create_object_notifications(db, "deleted", object=os_obj)
            _dispatch_if_subscribed(
                "object", "deleted", _reactor_object_payload(os_obj, object_uuid, event_uuid)
            )

    return True


@celery_app.task
def send_email(email: dict):
    logger.info("sending email job started")

    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = os.environ.get("MAIL_PORT")
    if not mail_server:
        logger.warning("MAIL_SERVER not configured, skipping email send")
        return False

    msg = EmailMessage()
    msg["Subject"] = email["subject"]
    msg["From"] = email["from"]
    msg["To"] = email["to"]
    msg.set_content(email["body"])

    try:
        with smtplib.SMTP(mail_server, mail_port) as server:
            username = os.environ.get("MAIL_USERNAME")
            password = os.environ.get("MAIL_PASSWORD")
            if username and password:
                server.login(username, password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        logger.error("Failed to send email: %s", e)
        return False

    return True


@celery_app.task(bind=True, queue=INGEST_QUEUE)
def fetch_feed(self, feed_id: int, user_id: int, queued: bool = False):
    logger.info("fetch feed id=%s job started", feed_id)

    held = _admit_ingest_run(self, "feed", feed_id, user_id, (feed_id, user_id), queued)
    if held is not None:
        return held

    try:
        with Session(engine) as db:
            user = users_repository.get_user_by_id(db, user_id)
            result = feeds_repository.fetch_feed(db, feed_id, user)
    except Exception as error:
        ingest_runs.finish("feed", feed_id, ingest_runs.FAILED, str(error))
        raise

    logger.info("fetch feed id=%s job finished: %s", feed_id, result["message"])
    return result


def _closes_feed_run(task_fn):
    """Close the feed's run when the single task ingesting it ends."""

    @functools.wraps(task_fn)
    def wrapper(feed_id: int, user_id: int):
        try:
            result = task_fn(feed_id, user_id)
        except Exception as error:
            ingest_runs.finish("feed", feed_id, ingest_runs.FAILED, str(error))
            raise
        ingest_runs.finish("feed", feed_id)
        return result

    return wrapper


# Kept for messages queued before feed fetches became runs (drain_ingest_run).
@celery_app.task(queue=INGEST_QUEUE)
def fetch_feed_event(event_uuid: str, feed_id: int, user_id: int):
    logger.info("fetch feed event uuid=%s job started", event_uuid)

    with Session(engine) as db, attributes_repository.bulk_ingest():
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        result = feeds_repository.process_feed_event(db, event_uuid, db_feed, user)

    logger.info("fetch feed event uuid=%s job finished", event_uuid)
    return result


@celery_app.task(
    queue=INGEST_QUEUE,
    soft_time_limit=SINGLE_FEED_SOFT_TIME_LIMIT,
    time_limit=SINGLE_FEED_SOFT_TIME_LIMIT + 60,
)
@_closes_feed_run
def fetch_csv_feed(feed_id: int, user_id: int):
    logger.info("fetch csv feed id=%s job started", feed_id)

    rows_parsed = 0
    attributes_created = 0
    failed_rows = 0

    with Session(engine) as db, attributes_repository.bulk_ingest():
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        if db_feed.input_source == "local":
            lines = feeds_repository.fetch_csv_content_from_local(db_feed.url)
        else:
            lines = feeds_repository.fetch_csv_content_from_network(
                db_feed.url, extra_headers=db_feed.headers
            )
        rows = feeds_repository.parse_csv_feed_lines(db_feed.settings, lines)
        has_header = feeds_repository.csv_feed_has_header(db_feed.settings)

        for index, row in enumerate(rows):
            if has_header and index == 0:
                continue  # skip the first line if header is present

            try:
                rows_parsed += 1
                attribute = feeds_repository.process_csv_feed_row(row, db_feed.settings)

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attribute["type"],
                    value=attribute["value"],
                    category=attribute.get("category", "External analysis"),
                )

                if "distribution" in attribute:
                    db_attribute.distribution = attribute["distribution"]

                if "comment" in attribute:
                    db_attribute.comment = attribute["comment"]

                if "to_ids" in attribute:
                    db_attribute.to_ids = attribute["to_ids"]

                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_rows += 1
                logger.error("Error processing CSV feed row: %s", e)

    events_repository.sync_event_counts(str(db_event.uuid))

    logger.info("fetch csv feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "CSV feed=%s processed, %s rows parsed, %s attributes created, %s rows failed."
        % (db_feed.name, rows_parsed, attributes_created, failed_rows),
    }


@celery_app.task(
    queue=INGEST_QUEUE,
    soft_time_limit=SINGLE_FEED_SOFT_TIME_LIMIT,
    time_limit=SINGLE_FEED_SOFT_TIME_LIMIT + 60,
)
@_closes_feed_run
def fetch_freetext_feed(feed_id: int, user_id: int):
    logger.info("fetch freetext feed id=%s job started", feed_id)

    rows_parsed = 0
    attributes_created = 0
    failed_rows = 0

    with Session(engine) as db, attributes_repository.bulk_ingest():
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        if db_feed.input_source == "local":
            lines = feeds_repository.fetch_csv_content_from_local(db_feed.url)
        else:
            lines = feeds_repository.fetch_csv_content_from_network(
                db_feed.url, extra_headers=db_feed.headers
            )

        freetext_config = (db_feed.settings or {}).get("freetextConfig", {})
        type_detection = freetext_config.get("type_detection", "automatic")
        fixed_type = freetext_config.get("fixed_type")

        for line in lines:
            value = line.strip()
            if not value:
                continue

            try:
                rows_parsed += 1

                if type_detection == "fixed" and fixed_type:
                    attr_type = fixed_type
                else:
                    attr_type = freetext_repository.detect_type(value)

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attr_type,
                    value=value,
                    category="External analysis",
                )
                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_rows += 1
                logger.error("Error processing freetext feed line: %s", e)

    events_repository.sync_event_counts(str(db_event.uuid))

    logger.info("fetch freetext feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "Freetext feed=%s processed, %s rows parsed, %s attributes created, %s rows failed."
        % (db_feed.name, rows_parsed, attributes_created, failed_rows),
    }


@celery_app.task(
    queue=INGEST_QUEUE,
    soft_time_limit=SINGLE_FEED_SOFT_TIME_LIMIT,
    time_limit=SINGLE_FEED_SOFT_TIME_LIMIT + 60,
)
@_closes_feed_run
def fetch_json_feed(feed_id: int, user_id: int):
    logger.info("fetch json feed id=%s job started", feed_id)

    items_processed = 0
    attributes_created = 0
    failed_items = 0

    with Session(engine) as db, attributes_repository.bulk_ingest():
        user = users_repository.get_user_by_id(db, user_id)
        db_feed = feeds_repository.get_feed_by_id(db, feed_id=feed_id)

        db_event = feeds_repository.get_or_create_feed_event(db, db_feed, user)

        if db_feed.input_source == "local":
            content = feeds_repository.fetch_json_content_from_local(db_feed.url)
        else:
            content = feeds_repository.fetch_json_content_from_network(
                db_feed.url, extra_headers=db_feed.headers
            )
        json_cfg = (db_feed.settings or {}).get("jsonConfig") or {}
        items = feeds_repository.parse_json_feed_items(content, json_cfg)

        for item in items:
            try:
                items_processed += 1
                attribute = feeds_repository.process_json_item_to_attribute(
                    item, db_feed.settings
                )

                if attribute.get("error") or not attribute.get("type") or not attribute.get("value"):
                    failed_items += 1
                    continue

                db_attribute = attribute_schemas.AttributeCreate(
                    event_uuid=db_event.uuid,
                    type=attribute["type"],
                    value=attribute["value"],
                    category=attribute.get("category", "External analysis"),
                )

                if "comment" in attribute:
                    db_attribute.comment = attribute["comment"]

                if "to_ids" in attribute:
                    db_attribute.to_ids = attribute["to_ids"]

                attributes_repository.create_attribute(db, db_attribute)
                attributes_created += 1

            except Exception as e:
                failed_items += 1
                logger.error("Error processing JSON feed item: %s", e)

    events_repository.sync_event_counts(str(db_event.uuid))

    logger.info("fetch json feed id=%s job finished", feed_id)

    return {
        "result": "success",
        "message": "JSON feed=%s processed, %s items, %s attributes created, %s failed."
        % (db_feed.name, items_processed, attributes_created, failed_items),
    }


@celery_app.task
def servo_backfill(run_id: int):
    """Re-run the ingest chain over attributes already indexed.

    Issues the `_update_by_query` and then polls OpenSearch's task API. The
    poll is bounded: a rewrite of a very large index can outlive any sensible
    worker occupancy, and leaving the run marked `running` with its task id
    stored is harmless because reading a run reconciles it against OpenSearch
    (`servos_repository.refresh_run`). The worker polling is a convenience, not
    the source of truth.
    """
    poll_seconds = 5
    max_polls = 360  # ~30 minutes before handing over to read-time reconcile

    with Session(engine) as db:
        db_run = servos_repository.get_run(db, run_id)
        if db_run is None:
            logger.warning("servo_backfill: run %s is gone", run_id)
            return False

        try:
            task_id = servo_chain.start_backfill(db_run.filter_query)
        except Exception as e:  # noqa: BLE001
            logger.exception("servo_backfill: could not start run %s", run_id)
            db_run.status = "failed"
            db_run.error = str(e)[:500]
            db_run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return False

        db_run.opensearch_task_id = task_id
        db_run.status = "running"
        db_run.started_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("servo_backfill run=%s opensearch_task=%s", run_id, task_id)

    for _ in range(max_polls):
        time.sleep(poll_seconds)
        with Session(engine) as db:
            db_run = servos_repository.get_run(db, run_id)
            if db_run is None:
                return False
            servos_repository.refresh_run(db, db_run)
            if db_run.status not in ("queued", "running"):
                logger.info(
                    "servo_backfill run=%s finished status=%s updated=%s",
                    run_id,
                    db_run.status,
                    db_run.updated,
                )
                return db_run.status == "success"

    logger.info(
        "servo_backfill run=%s still running; leaving it to read-time reconcile",
        run_id,
    )
    return True


@celery_app.task(queue=MAINTENANCE_QUEUE)
def generate_correlations():
    logger.info("generate correlations job started")

    with Session(engine) as db:
        runtimeSettings = get_runtime_settings(db)

    try:
        RedisClient = get_redis_client()
    except Exception:
        RedisClient = None

    # TODO: Make lock key and TTL configurable, check if this is still required when there are multiple workers
    lock_key = "generate_correlations_lock"
    lock_ttl_seconds = 60 * 60 * 1  # 1 hour - safe default for long runs

    # Try to acquire the lock. If we can't acquire it, another run is active
    # or finished very recently, so skip to avoid duplicates.
    if RedisClient is not None:
        try:
            got_lock = RedisClient.set(lock_key, "1", nx=True, ex=lock_ttl_seconds)
        except Exception:
            got_lock = False
    else:
        got_lock = False

    if not got_lock:
        logger.info("generate_correlations skipped: lock present (another run active)")
        return True

    try:
        try:
            correlations_repository.delete_correlations()
            correlations_repository.run_correlations(runtimeSettings)
        except Exception as e:
            logger.error("Failed to generate correlations: %s", str(e))
            return False

        logger.info("generate correlations job finished")
        run_correlation_hunts.delay()
        return True
    finally:
        # Release the lock. If Redis isn't available this is a noop.
        try:
            if RedisClient is not None:
                RedisClient.delete(lock_key)
        except Exception:
            pass


@celery_app.task(queue=MAINTENANCE_QUEUE)
def enforce_retention():
    logger.info("enforce_retention job started")
    with Session(engine) as db:
        runtime_settings = get_runtime_settings(db)

    retention = runtime_settings.get("retention") or {}
    if not retention.get("enabled"):
        logger.info("enforce_retention skipped: retention disabled")
        return True

    period_days = retention.get("period_days", 365)
    exempt_tags = retention.get("exempt_tags", ["retention:exempt"])
    cutoff = int(datetime.now().timestamp()) - period_days * 86400
    client = get_opensearch_client()

    must_not = (
        [{"match_phrase": {"tags.name": tag}} for tag in exempt_tags]
        if exempt_tags
        else []
    )

    # Collect all event UUIDs eligible for retention
    event_uuids = []
    search_after = None
    while True:
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"lt": cutoff}}},
                        {"term": {"deleted": False}},
                    ],
                    "must_not": must_not,
                }
            },
            "_source": ["uuid"],
            "size": 500,
            "sort": [{"uuid.keyword": "asc"}],
        }
        if search_after:
            body["search_after"] = search_after
        response = client.search(index="misp-events", body=body)
        hits = response["hits"]["hits"]
        if not hits:
            break
        event_uuids.extend(hit["_source"]["uuid"] for hit in hits)
        if len(hits) < 500:
            break
        search_after = hits[-1]["sort"]

    if not event_uuids:
        logger.info("enforce_retention finished: no events to purge")
        return True

    logger.info("enforce_retention: purging %s events", len(event_uuids))

    for event_uuid in event_uuids:
        logger.info("enforce_retention: purging event uuid=%s", event_uuid)

        # Collect attribute UUIDs for sighting cleanup
        attr_resp = client.search(
            index="misp-attributes",
            body={
                "query": {"term": {"event_uuid": event_uuid}},
                "_source": ["uuid"],
                "size": 10000,
            },
        )
        attr_uuids = [h["_source"]["uuid"] for h in attr_resp["hits"]["hits"]]

        # Delete sightings for these attributes
        if attr_uuids:
            client.delete_by_query(
                index="misp-sightings",
                body={"query": {"terms": {"attribute_uuid.keyword": attr_uuids}}},
                refresh=False,
                ignore=[404],
            )

        # Delete correlations
        correlations_repository.delete_event_correlations(event_uuid)

        # Delete event, attributes, and objects
        delete_indexed_event(event_uuid)

    logger.info("enforce_retention finished: %s events purged", len(event_uuids))
    return True


@celery_app.task
def handle_created_sightings(items: list):
    """Post-process a batch of sightings: notifications, reactor, FP feedback.

    One task per batch (see sightings_repository.TASK_BATCH_SIZE): attributes
    are looked up for all values in one paged query instead of one search per
    sighting.
    """
    from app.repositories import sightings as sightings_repository

    logger.info("handling %s created sightings job started", len(items))
    with Session(engine) as db:
        result = sightings_repository.process_created_sightings(db, items)

    if reactor_repository.has_active_subscriber("sighting", "created"):
        for item in items:
            _dispatch_if_subscribed(
                "sighting",
                "created",
                {
                    "value": item["value"],
                    "type": item["type"],
                    "organisation": item.get("organisation"),
                    "timestamp": item.get("timestamp"),
                },
            )
    logger.info("handling %s created sightings job finished: %s", len(items), result)
    return result


@celery_app.task
def handle_created_sighting(
    value: str, organisation: str, sighting_type: str, timestamp: float = None
):
    """Single-sighting form, kept for messages queued before the batch task."""
    return handle_created_sightings(
        [
            {
                "value": value,
                "type": sighting_type,
                "organisation": organisation,
                "timestamp": timestamp or datetime.now().timestamp(),
            }
        ]
    )


@celery_app.task
def handle_created_correlation(
    source_attribute_uuid: str,
    source_event_uuid: str,
    target_event_uuid: str,
    target_attribute_uuid: str,
    target_attribute_type: str,
    target_attribute_value: str,
):
    logger.info("handling created correlation id=%s job started", source_attribute_uuid)

    handle_created_correlations(
        [
            {
                "source_attribute_uuid": source_attribute_uuid,
                "source_event_uuid": source_event_uuid,
                "target_event_uuid": target_event_uuid,
                "target_attribute_uuid": target_attribute_uuid,
                "target_attribute_type": target_attribute_type,
                "target_attribute_value": target_attribute_value,
            }
        ]
    )

    return True


@celery_app.task
def handle_created_correlations(correlations: list[dict]):
    """Handle a batch of created correlations in one go.

    Correlation runs produce them in bulk, so notifications are written from a
    single session instead of one task, session and commit per correlation.
    """
    logger.info("handling %s created correlations job started", len(correlations))

    if not correlations:
        return True

    with Session(engine) as db:
        notifications_repository.create_correlation_notifications_bulk(
            db, "created", correlations
        )

    for correlation in correlations:
        _dispatch_if_subscribed("correlation", "created", correlation)

    logger.info("handling %s created correlations job finished", len(correlations))

    return True


@celery_app.task
def handle_published_event(event_uuid: str):
    logger.info("handling published event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "published", event=os_event)
            from app.repositories import sinks as sinks_repository

            sinks_repository.dispatch_published_event(db, event_uuid)
        _dispatch_if_subscribed("event", "published", _reactor_event_payload(os_event, event_uuid))

    logger.info("handling published event uuid=%s job finished", event_uuid)
    return True


@celery_app.task
def handle_unpublished_event(event_uuid: str):
    logger.info("handling unpublished event uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is not None:
        with Session(engine) as db:
            notifications_repository.create_event_notifications(db, "unpublished", event=os_event)
        _dispatch_if_subscribed("event", "unpublished", _reactor_event_payload(os_event, event_uuid))

    logger.info("handling unpublished event uuid=%s job finished", event_uuid)
    return True


@celery_app.task(queue=INGEST_QUEUE)
def handle_created_attributes(items: list):
    """Handle a batch of created attributes: notifications and reactor dispatch.

    An ingest creates attributes in the thousands, and one task per attribute is
    a broker round trip, a session and an OpenSearch get each. Counting and
    correlating are already batched; this is the rest of the per attribute work.

    Each item is ``[attribute_uuid, object_uuid, event_uuid]``.
    """
    logger.info("handling %s created attributes job started", len(items))

    if not items:
        return True

    with Session(engine) as db:
        for attribute_uuid, object_uuid, event_uuid in items:
            os_attr = attributes_repository.get_attribute_from_opensearch(
                UUID(attribute_uuid)
            )

            if os_attr is None:
                continue

            notifications_repository.create_attribute_notifications(
                db, "created", attribute=os_attr
            )
            _dispatch_if_subscribed(
                "attribute",
                "created",
                _reactor_attribute_payload(
                    os_attr, attribute_uuid, object_uuid, event_uuid
                ),
                queue=INGEST_QUEUE,
            )

    logger.info("handling %s created attributes job finished", len(items))

    return True


def correlations_enabled(runtimeSettings) -> bool:
    return bool(runtimeSettings.get_value("correlations.correlateOnChange", True))


def enqueue_deferred_correlations(batch: dict):
    """Enqueue the follow-up tasks a bulk ingest collected.

    Everything is split into fixed size chunks so a large feed or pull spreads
    over the workers instead of riding in one oversized message.
    """
    for rebuild, key in ((False, "created"), (True, "updated")):
        attribute_uuids = batch.get(key) or []

        for start in range(0, len(attribute_uuids), CORRELATION_BATCH_SIZE):
            correlate_attributes.delay(
                attribute_uuids[start : start + CORRELATION_BATCH_SIZE], rebuild
            )

    handled = batch.get("handled") or []
    for start in range(0, len(handled), CORRELATION_BATCH_SIZE):
        handle_created_attributes.delay(
            handled[start : start + CORRELATION_BATCH_SIZE]
        )

    logger.info(
        "enqueued follow-ups for %s created and %s updated attributes",
        len(batch.get("created") or []),
        len(batch.get("updated") or []),
    )


@celery_app.task(queue=INGEST_QUEUE)
def correlate_attributes(attribute_uuids: list[str], rebuild: bool = False):
    """Correlate a batch of attributes produced by a bulk ingest."""
    logger.info("correlating %s attributes job started", len(attribute_uuids))

    with Session(engine) as db:
        runtimeSettings = get_runtime_settings(db)

    if not correlations_enabled(runtimeSettings):
        logger.info(
            "correlating attributes skipped: correlations.correlateOnChange is off"
        )
        return True

    result = correlations_repository.correlate_attribute_uuids(
        runtimeSettings, attribute_uuids, rebuild=rebuild
    )

    logger.info(
        "correlating %s attributes job finished, %s correlations stored",
        len(attribute_uuids),
        result["stored"],
    )

    return True


@celery_app.task
def correlate_attribute(attribute_uuid: str):
    """Correlate a single attribute, enqueued whenever one is created or changed."""
    logger.info("correlating attribute uuid=%s job started", attribute_uuid)

    with Session(engine) as db:
        runtimeSettings = get_runtime_settings(db)

    if not correlations_enabled(runtimeSettings):
        logger.info(
            "correlating attribute uuid=%s skipped: correlations.correlateOnChange is off",
            attribute_uuid,
        )
        return True

    result = correlations_repository.correlate_attribute(runtimeSettings, attribute_uuid)

    logger.info(
        "correlating attribute uuid=%s job finished, %s correlations stored",
        attribute_uuid,
        result["stored"],
    )

    return True


@celery_app.task
def handle_toggled_event_correlation(event_uuid: str, disable_correlation: bool):
    logger.info("handling toggled event correlation uuid=%s job started", event_uuid)

    os_event = events_repository.get_event_from_opensearch(UUID(event_uuid))
    if os_event is None:
        logger.warning("handle_toggled_event_correlation: event %s not found", event_uuid)
        return True

    if disable_correlation:
        correlations_repository.delete_event_correlations(event_uuid)
    else:
        with Session(engine) as db:
            runtimeSettings = get_runtime_settings(db)
        correlations_repository.correlate_event(runtimeSettings, str(event_uuid))
        run_correlation_hunts.delay()

    logger.info("handling toggled event correlation uuid=%s job finished", event_uuid)
    return True


@celery_app.task
def delete_indexed_event(event_uuid: str):
    logger.info("deleting indexed event uuid=%s job started", event_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-events", id=event_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info("event uuid=%s not found in index, nothing to delete", event_uuid)
    else:
        logger.info("deleted indexed event uuid=%s", event_uuid)

    # delete indexed attributes
    query = {"query": {"bool": {"must": [{"term": {"event_uuid": str(event_uuid)}}]}}}

    response = OpenSearchClient.delete_by_query(
        index="misp-attributes", body=query, refresh=True, ignore=[404]
    )
    logger.info(
        "deleted %s indexed attributes for event uuid=%s",
        response.get("deleted", 0),
        event_uuid,
    )

    # delete indexed objects
    response = OpenSearchClient.delete_by_query(
        index="misp-objects", body=query, refresh=True, ignore=[404]
    )
    logger.info(
        "deleted %s indexed objects for event uuid=%s",
        response.get("deleted", 0),
        event_uuid,
    )

    logger.info("deleting indexed event uuid=%s job finished", event_uuid)

    return True


@celery_app.task
def delete_indexed_attribute(attribute_uuid: str):
    logger.info("deleting indexed attribute uuid=%s job started", attribute_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-attributes", id=attribute_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info(
            "attribute uuid=%s not found in index, nothing to delete", attribute_uuid
        )
    else:
        logger.info("deleted indexed attribute uuid=%s", attribute_uuid)

    logger.info("deleting indexed attribute uuid=%s job finished", attribute_uuid)

    return True


@celery_app.task(queue=MAINTENANCE_QUEUE)
def load_galaxies(user_id: int):
    """Load galaxies from the bundled misp-galaxy submodule into the database.

    If `user_id` is not provided the first user in the database will be used as
    the creator for created tags and objects.
    """
    logger.info("load_galaxies job started")

    with Session(engine) as db:
        user = None
        if user_id is not None:
            user = users_repository.get_user_by_id(db, user_id)
        if user is None:
            first = users_repository.get_users(db, skip=0, limit=1)
            user = first[0] if first else None

        if user is None:
            logger.error("No user found to run load_galaxies; aborting")
            return False

        try:
            galaxies = galaxies_repository.update_galaxies(db, user)
            logger.info(
                "load_galaxies finished: %s galaxies created/updated", len(galaxies)
            )
            return True
        except Exception as e:
            logger.exception("Error loading galaxies: %s", e)
            return False


@celery_app.task(queue=MAINTENANCE_QUEUE)
def load_taxonomies():
    logger.info("load_taxonomies job started")

    with Session(engine) as db:
        try:
            taxonomies = taxonomies_repository.update_taxonomies(db)
            logger.info(
                "load_taxonomies finished: %s taxonomies created/updated",
                len(taxonomies),
            )
            return True
        except Exception as e:
            logger.exception("Error loading taxonomies: %s", e)
            return False


@celery_app.task
def delete_indexed_object(object_uuid: str):
    logger.info("deleting indexed object uuid=%s job started", object_uuid)

    OpenSearchClient = get_opensearch_client()

    response = OpenSearchClient.delete(
        index="misp-objects", id=object_uuid, refresh=True, ignore=[404]
    )

    if response.get("result") == "not_found":
        logger.info("object uuid=%s not found in index, nothing to delete", object_uuid)
    else:
        logger.info("deleted indexed object uuid=%s", object_uuid)

    logger.info("deleting indexed object uuid=%s job finished", object_uuid)

    return True


@celery_app.task
def run_hunt(hunt_id: int, **kwargs):
    logger.info("run hunt id=%s job started", hunt_id)

    with Session(engine) as db:
        result = hunts_repository.execute_hunt_system(db, hunt_id=hunt_id)
        total = result["total"] if result else 0
        logger.info("run hunt id=%s finished, %s matches", hunt_id, total)

    return True


@celery_app.task(queue=MAINTENANCE_QUEUE)
def run_correlation_hunts():
    """Re-run all active correlation hunts. Called after correlations are regenerated."""
    logger.info("run_correlation_hunts job started")
    with Session(engine) as db:
        hunts = hunts_repository.get_active_correlation_hunts(db)
        for hunt in hunts:
            run_hunt.delay(hunt.id)
    logger.info("run_correlation_hunts job finished, %s hunts queued", len(hunts))
    return True


@celery_app.task
def dummy_sleep(duration: int = 600):
    logger.info("dummy_sleep job started, sleeping for %s seconds", duration)
    time.sleep(duration)
    logger.info("dummy_sleep job finished")
    return {"slept_for": duration}


# ──────────────────────────────────────────────────────────────────────────
# Tech Lab — Reactor Scripts
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task
def reactor_dispatch(resource_type: str, action: str, payload: dict):
    """Find scripts subscribed to (resource_type, action) and queue runs.

    Cheap lookup that runs on the default queue alongside the existing
    `handle_*` tasks. Actual script execution happens on the
    ``reactor_sandbox`` queue served by an isolated worker container.
    """
    with Session(engine) as db:
        # The gate fell open to get here; close it if it was only cold.
        reactor_repository.warm_active_triggers_cache(db)
        reactor_repository.dispatch_triggered_scripts(db, resource_type, action, payload)
    return True


@celery_app.task(queue="reactor_sandbox", time_limit=300, soft_time_limit=240)
def run_reactor_script(run_id: int):
    """Execute a reactor script run. Container provides the real isolation."""
    logger.info("run_reactor_script run_id=%s started", run_id)
    with Session(engine) as db:
        reactor_runner.run_script(db, run_id)
    logger.info("run_reactor_script run_id=%s finished", run_id)
    return True


# ──────────────────────────────────────────────────────────────────────────
# Tech Lab — Notebooks
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task(queue="lab_kernel", time_limit=600, soft_time_limit=540)
def lab_execute_cell(execution_id: int, timeout_seconds: int = 60):
    """Run one queued cell execution. Lives on the lab-worker container."""
    logger.info("lab_execute_cell execution_id=%s started", execution_id)
    with Session(engine) as db:
        lab_executor.execute_cell(db, execution_id, timeout_seconds=timeout_seconds)
    logger.info("lab_execute_cell execution_id=%s finished", execution_id)
    return True


@celery_app.task(queue="lab_kernel")
def lab_kernel_interrupt(user_id: int, notebook_id: int):
    lab_kernel_manager.get_default_registry().interrupt((user_id, notebook_id))
    return True


@celery_app.task(queue="lab_kernel")
def lab_kernel_shutdown(user_id: int, notebook_id: int):
    lab_kernel_manager.get_default_registry().shutdown((user_id, notebook_id))
    return True


@celery_app.task(queue="lab_kernel")
def lab_kernel_list():
    """Snapshot of running kernels for the diagnostics endpoint."""
    return lab_kernel_manager.get_default_registry().snapshot()


# ──────────────────────────────────────────────────────────────────────────
# Exports — async IOC export jobs
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task(time_limit=720, soft_time_limit=600)
def run_export(export_id: int, **kwargs):
    """Run an IOC export job: query OpenSearch, transform, store the artifact.

    The soft time limit raises SoftTimeLimitExceeded inside ``run_export``,
    which records the job as failed rather than leaving it stuck on "running".

    ``**kwargs`` absorbs scheduler-injected arguments (e.g. ``user_id``) when
    the task is triggered by a recurring redbeat schedule.
    """
    logger.info("run_export export_id=%s started", export_id)
    from app.repositories import exports as exports_repository

    with Session(engine) as db:
        exports_repository.run_export(db, export_id)
    logger.info("run_export export_id=%s finished", export_id)
    return True


# ──────────────────────────────────────────────────────────────────────────
# Sinks — push published indicators to SIEMs
# ──────────────────────────────────────────────────────────────────────────

# Retry delays: 30s, 1m, 2m, 4m, 8m, 16m (plus jitter), then give up.
SINK_MAX_RETRIES = 6
SINK_RETRY_BASE_SECONDS = 30


def _deliver_with_retries(task, sink_id: int, label: str, deliver):
    """Run ``deliver(sink)`` for an enabled sink, retrying on transport errors.

    The error is recorded on the sink after every attempt, and the delivery
    counted as failed once retries run out.
    """
    import random

    from app.repositories import sinks as sinks_repository
    from app.services.sinks.transports import SinkDeliveryError

    with Session(engine) as db:
        sink = sinks_repository.get_sink(db, sink_id)
        if sink is None or not sink.enabled:
            return 0
        try:
            sent = deliver(sink)
        except SinkDeliveryError as error:
            final = task.request.retries >= task.max_retries
            sinks_repository.record_failure(db, sink_id, str(error), final=final)
            logger.warning(
                "sink %s delivery of %s failed (attempt %s): %s",
                sink_id,
                label,
                task.request.retries + 1,
                error,
            )
            if final:
                return 0
            countdown = SINK_RETRY_BASE_SECONDS * 2 ** task.request.retries
            raise task.retry(
                exc=error, countdown=countdown + random.uniform(0, countdown / 4)
            )
        sinks_repository.record_success(db, sink_id, sent)
        logger.info("sink %s delivered %s attributes of %s", sink_id, sent, label)
        return sent


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def sync_sink_memberships():
    """Queue a membership sync of every sink that keeps in step with a profile."""
    from app.repositories import sinks as sinks_repository

    with Session(engine) as db:
        sink_ids = sinks_repository.membership_sinks(db)
    for sink_id in sink_ids:
        sync_sink_membership.apply_async((sink_id,), queue="sinks")
    return len(sink_ids)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def evaluate_local_warninglists():
    """Recompute the members of every organisation's list."""
    from app.repositories import local_warninglists

    with Session(engine) as db:
        return local_warninglists.evaluate_all(db)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def evaluate_recent_local_warninglists():
    """Match the indicators written since the last run."""
    from app.repositories import local_warninglists

    with Session(engine) as db:
        return local_warninglists.evaluate_recent(db)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def sweep_local_warninglists():
    """Expire organisations' warninglist entries and sync due sources."""
    from app.repositories import local_warninglists

    with Session(engine) as db:
        return local_warninglists.sweep(db)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def refresh_edls():
    """Rebuild the external dynamic lists due."""
    from app.repositories import edls

    with Session(engine) as db:
        return edls.refresh_due(db)


@celery_app.task(ignore_result=True)
def build_edl(edl_id: int):
    """Rebuild one external dynamic list now (created, edited, approved)."""
    from app.models import edl as edl_models
    from app.repositories import edls

    with Session(engine) as db:
        edl = db.get(edl_models.Edl, edl_id)
        if edl is not None:
            edls.build(db, edl)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True)
def check_profile_gates():
    """Look ahead at every detection profile with an approval gate."""
    from app.repositories import profile_gate

    return profile_gate.check_all()


@celery_app.task(bind=True, queue="sinks", max_retries=SINK_MAX_RETRIES)
def sync_sink_membership(self, sink_id: int):
    """Send one sink what joined and left its profile since its last sync."""
    from app.repositories import sinks as sinks_repository

    return _deliver_with_retries(
        self, sink_id, "membership changes", sinks_repository.deliver_membership
    )


@celery_app.task(bind=True, queue="sinks", max_retries=SINK_MAX_RETRIES)
def deliver_to_sink(self, sink_id: int, event_uuid: str, apply_filters: bool = True):
    """Push one event's selected attributes to one sink.

    Runs on the dedicated ``sinks`` queue, retried with exponential backoff.
    ``apply_filters=False`` (sends from code) skips the sink's selection
    filters but never its exclusions.
    """
    from app.repositories import sinks as sinks_repository

    return _deliver_with_retries(
        self,
        sink_id,
        f"event {event_uuid}",
        lambda sink: sinks_repository.deliver_event(sink, event_uuid, apply_filters),
    )


@celery_app.task(bind=True, queue="sinks", max_retries=SINK_MAX_RETRIES)
def deliver_items_to_sink(
    self, sink_id: int, mode: str, items: list, apply_filters: bool = True
):
    """Push attributes (by uuid) or caller-built records to one sink.

    Queued by sends from notebooks and reactor scripts
    (``app.services.sinks.send``), at most a thousand items per task.
    """
    from app.repositories import sinks as sinks_repository

    deliver = {
        "attributes": sinks_repository.deliver_attributes,
        "records": sinks_repository.deliver_records,
    }[mode]
    return _deliver_with_retries(
        self,
        sink_id,
        f"{len(items)} {mode}",
        lambda sink: deliver(sink, items, apply_filters),
    )


# ──────────────────────────────────────────────────────────────────────────
# Lookup — Redis prefilter of indicator values
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True, expires=15)
def sync_lookup_cache():
    """Add values of indicators written since the last sync to the prefilter."""
    from app.repositories import lookup as lookup_repository

    return lookup_repository.sync_cache()


@celery_app.task(
    queue=MAINTENANCE_QUEUE,
    ignore_result=True,
    time_limit=1800,
    soft_time_limit=1700,
)
def rebuild_lookup_cache():
    """Rebuild the lookup prefilter from OpenSearch, dropping stale values."""
    from app.repositories import lookup as lookup_repository

    return lookup_repository.rebuild_cache()


# ──────────────────────────────────────────────────────────────────────────
# Consolidated indicators
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task(
    queue=MAINTENANCE_QUEUE,
    ignore_result=True,
    expires=15,
    time_limit=2 * 3600,
)
def sync_indicators():
    """Refresh the indicators of values written or sighted since the last sync."""
    from app.repositories import indicators as indicators_repository

    return indicators_repository.sync()


@celery_app.task(
    queue=MAINTENANCE_QUEUE,
    ignore_result=True,
    time_limit=4 * 3600,
    soft_time_limit=4 * 3600 - 60,
)
def rebuild_indicators(requested: bool = False):
    """Recompute every indicator; tombstone those without live attributes.

    ``requested`` (by request_rebuild: a source's trust or the scoring settings
    changed): every changed score is written, and when a sync or another
    rebuild holds the lock the rebuild is retried shortly, not dropped. The
    hourly run just skips a turn.
    """
    from app.repositories import indicators as indicators_repository

    result = indicators_repository.rebuild(requested=requested)
    if result is None and requested:
        rebuild_indicators.apply_async(
            kwargs={"requested": True},
            countdown=indicators_repository.REBUILD_RETRY_SECONDS,
        )
    return result


# ──────────────────────────────────────────────────────────────────────────
# Warninglists
# ──────────────────────────────────────────────────────────────────────────


@celery_app.task(queue=MAINTENANCE_QUEUE, time_limit=3600, soft_time_limit=3500)
def load_warninglists():
    """Load the misp-warninglists submodule, then re-flag attributes if needed."""
    from app.repositories import warninglists as warninglists_repository

    with Session(engine) as db:
        counts = warninglists_repository.update_warninglists(db)
    if counts["changed"]:
        evaluate_all_warninglist_hits.delay()
    return counts


@celery_app.task(
    queue=MAINTENANCE_QUEUE,
    time_limit=4 * 3600,
    soft_time_limit=4 * 3600 - 60,
)
def evaluate_all_warninglist_hits():
    """Re-evaluate every live attribute against the enabled warninglists."""
    from app.repositories import warninglists as warninglists_repository

    with Session(engine) as db:
        return warninglists_repository.evaluate_all(db)


@celery_app.task(queue=MAINTENANCE_QUEUE, ignore_result=True, expires=60)
def evaluate_recent_warninglist_hits():
    """Flag attributes written since the last run."""
    from app.repositories import warninglists as warninglists_repository

    with Session(engine) as db:
        return warninglists_repository.evaluate_recent(db)
