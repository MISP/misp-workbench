import os
import logging
from hashlib import sha1
from typing import Union
from uuid import UUID

from datetime import datetime
from app.models import event as event_models
from app.models import server as server_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.models import attribute as attribute_models
from app.models import object as object_models
from app.models.event import DistributionLevel
from app.repositories import attributes as attributes_repository
from app.repositories import sync as sync_repository
from app.repositories import events as events_repository
from app.repositories import objects as objects_repository
from app.repositories import sharing_groups as sharing_groups_repository
from app.repositories import tags as tags_repository
from app.schemas import server as server_schemas
from app.settings import Settings
from fastapi import HTTPException, status
from pymisp import (
    MISPAttribute,
    MISPEvent,
    MISPObject,
    MISPSharingGroup,
    MISPTag,
    MISPEventReport,
    PyMISP,
)
from sqlalchemy.orm import Session
from app.worker import tasks
from app.dependencies import get_opensearch_client

logger = logging.getLogger(__name__)


def get_servers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(server_models.Server).offset(skip).limit(limit).all()


def get_server_by_id(db: Session, server_id: int):
    return (
        db.query(server_models.Server)
        .filter(server_models.Server.id == server_id)
        .first()
    )


def create_server(db: Session, server: server_schemas.ServerCreate):
    db_server = server_models.Server(
        name=server.name,
        url=server.url,
        authkey=server.authkey,
        org_id=server.org_id,
        push=server.push,
        pull=server.pull,
        push_sightings=server.push_sightings,
        push_galaxy_clusters=server.push_galaxy_clusters,
        pull_galaxy_clusters=server.pull_galaxy_clusters,
        last_pulled_id=server.last_pulled_id,
        last_pushed_id=server.last_pushed_id,
        organisation=server.organisation,
        remote_org_id=server.remote_org_id,
        publish_without_email=server.publish_without_email,
        unpublish_event=server.unpublish_event,
        self_signed=server.self_signed,
        pull_rules=server.pull_rules,
        push_rules=server.push_rules,
        cert_file=server.cert_file,
        client_cert_file=server.client_cert_file,
        internal=server.internal,
        skip_proxy=server.skip_proxy,
        caching_enabled=server.caching_enabled,
        priority=server.priority,
    )

    db.add(db_server)
    db.commit()
    db.refresh(db_server)

    return db_server


def get_remote_misp_connection(server: server_models.Server):
    verify_cert = not server.self_signed

    try:
        remote_misp = PyMISP(url=server.url, key=server.authkey, ssl=verify_cert, http_headers={"User-Agent": "misp-lite/" + os.environ.get("APP_VERSION", "")})
        remote_misp_version = remote_misp.misp_instance_version
    except Exception as ex:
        raise Exception("Remote MISP instance not reachable: %s" % ex)
    # check sync permissions
    if not remote_misp_version["perm_sync"]:
        raise Exception("Not authorized to sync from remote MISP instance")

    return remote_misp


def pull_server_by_id(
    db: Session,
    settings: Settings,
    server_id: int,
    user: user_models.User,
    technique: str = "full",
):
    """
    see: app/Model/Server.php::pull()
    """

    server = get_server_by_id(db, server_id)
    if server is None:
        raise Exception("Server not found")

    # get remote instance version
    remote_misp = get_remote_misp_connection(server)

    if technique == "pull_relevant_clusters":
        # TODO implement pull_relevant_clusters server pull technique
        raise Exception("Server pull technique `pull_relevant_clusters` not implemented yet.")

    if technique == "update":
        # TODO implement update server pull technique
        raise Exception("Server pull technique `update` not implemented yet.")

    if technique == "full":
        return pull_server_by_id_full(db, server, remote_misp, user)

    raise Exception("Unknown server pull technique `%s` not implemented yet." % technique)


def pull_server_by_id_full(
    db: Session,
    server: server_schemas.Server,
    remote_misp: PyMISP,
    user: user_models.User,
):

    # get a list of the event_ids on the server
    event_uuids = get_event_uuids_from_server(server, remote_misp)

    # TODO apply MISP.enableEventBlocklisting / removeBlockedEvents
    # TODO apply MISP.enableOrgBlocklisting / removeBlockedEvents

    # pull each of the events in different tasks
    for event_uuid in event_uuids:
        tasks.pull_event_by_uuid.delay(event_uuid, server.id, user.id)

    logger.info("server pull id=%s all event fetch tasks enqueued.", server.id)
    return {"result": "success", "message": "All server id=%s events to pull enqueued." % server.id}


def get_event_uuids_from_server(server: server_schemas.Server, remote_misp: PyMISP):
    """
    see: app/Model/Server.php::getEventIndexFromServer()
    """

    # TODO: apply filter rules / ignoreFilterRules
    # TODO: use restSearch and pagination
    events = remote_misp.search_index(minimal=True, published=True)
    event_ids = [event["uuid"] for event in events]

    return event_ids


def pull_event_by_uuid(
    db: Session,
    event_uuid: str,
    server: server_schemas.Server,
    user: user_models.User,
    settings: Settings,
):
    """
    see: app/Model/Server.php::__pullEvent()
    """
    
    remote_misp = get_remote_misp_connection(server)

    # fetch event from remote server
    data = {
        "deleted": [0, 1],
        "excludeGalaxy": 1,
        "includeEventCorrelations": 0,
        "includeFeedCorrelations": 0,
        "includeWarninglistHits": 0,
        "withAttachments": 1
    }

    if server.internal:
        data["excludeLocalTags"] = 1

    try:
        response = remote_misp._prepare_request(
            "POST", f"events/view/{event_uuid}", data=data
        )
        event_raw = remote_misp._check_json_response(response)
        event = MISPEvent()
        event.load(event_raw)
    except Exception as ex:
        logger.error(
            "Failed downloading the event {} from remote server {}".format(
                event_uuid, server.id
            ),
            ex,
        )
        return False

    if event is None:
        logger.error(
            "Empty event returned from the event {} from remote server {}".format(
                event_uuid, server.id
            )
        )
        return False

    event = update_pulled_event_before_insert(db, settings, event, server, user)

    if not check_if_event_is_not_empty:
        logger.info("Event %s is empty, skipping" % event_uuid)
        return False

    db_event = create_or_update_pulled_event(db, event, server, user)

    if not db_event:
        return False

    # TODO: process cryptographic keys, see app/Model/Event.php::_add()

    # TODO: process sightings, see app/Model/Event.php::_add()

    # TODO: process tag collection, see app/Model/Event.php::_add()
    
    tasks.index_event.delay(db_event.uuid)

    return True


def update_pulled_event_before_insert(
    db: Session,
    settings: Settings,
    event: MISPEvent,
    server: server_schemas.Server,
    user: user_models.User,
):
    """
    see: app/Model/Server.php::__updatePulledEventBeforeInsert()
    see: app/Model/Event.php::_add()
    """

    event.locked = True

    if (
        settings.MISP.host_org_id is None
        or not server.internal
        or settings.MISP.host_org_id != server.org_id
    ):
        # update event distribution level
        event.distribution = downgrade_distribution(event.distribution)

        # remove local tags obtained via pull
        event.tags = [tag for tag in event.tags if not tag.local]

        # process objects
        if event.objects:
            for object in event.objects:
                object = update_pulled_object_before_insert(object)

        # process attributes
        if event.attributes:
            for attribute in event.attributes:
                attribute = update_pulled_attribute_before_insert(attribute)


        # process event reports
        if event.event_reports:
            # TODO handle event reports
            pass

    # these transformations come from app/Model/Event.php::_add()
    event.org_id = server.org_id

    if event.orgc_id is not None and event.orgc is not None:
        event.orgc_id = event.org_id

    if not user.can_create_pulled_event(event):
        logger.warning(
            "User {} is not authorized to create events in org {}".format(
                user.id, event.org_id
            )
        )

    event.id = None

    if not user.can_publish_event():
        event.published = False

    event.user_id = user.id

    return event


def update_pulled_attribute_before_insert(attribute: MISPAttribute) -> MISPAttribute:
    # TODO: handle MISP.enable_synchronisation_filtering_on_type / attributes pullRules

    attribute.distribution = downgrade_distribution(attribute.distribution)
    
    if attribute.object_id == "0":
        attribute.object_id = None
        
    # remove local tags obtained via pull
    attribute.tags = [tag for tag in attribute.tags if not tag.local]

    return attribute


def update_pulled_object_before_insert(object: MISPObject) -> MISPObject:
    # TODO: handle MISP.enable_synchronisation_filtering_on_type / attributes pullRules

    object.distribution = downgrade_distribution(object.distribution)

    for attribute in object.attributes:
        attribute = update_pulled_attribute_before_insert(attribute)

    return object


def downgrade_distribution(distribution: DistributionLevel) -> DistributionLevel:
    if distribution is None:
        return DistributionLevel.COMMUNITY_ONLY

    if distribution == DistributionLevel.COMMUNITY_ONLY:
        # if community only, downgrade to organisation only after pull
        return DistributionLevel.ORGANISATION_ONLY
    elif distribution == DistributionLevel.CONNECTED_COMMUNITIES:
        # if connected communities downgrade to community only
        return DistributionLevel.COMMUNITY_ONLY

    return distribution


def check_if_event_is_not_empty(event: MISPEvent) -> bool:
    """
    see: app/Model/Server.php::__checkIfEventSaveAble()
    """
    if any(attribute for attribute in event.attributes if not attribute.deleted):
        return True

    if any(
        object
        for object in event.objects
        if not object.deleted
        and any(attribute for attribute in object.attributes if not attribute.deleted)
    ):
        return True

    if any(
        event_report for event_report in event.event_reports if not event_report.deleted
    ):
        return True

    return False


def create_or_update_pulled_event(
    db: Session, event: MISPEvent, server: server_schemas.Server, user: user_models.User
) -> Union[MISPEvent, bool]:
    """
    see: app/Model/Server.php::__checkIfPulledEventExistsAndAddOrUpdate()
    """
    existing_event = events_repository.get_event_by_uuid(db, event_uuid=event.uuid)

    if existing_event is None:
        # create event

        # TODO: handle protected event

        if event.sharing_group_id > 0:
            event.sharing_group_id = create_pulled_event_sharing_group(
                db, event.SharingGroup, server, user
            )
        else:
            event.sharing_group_id = None

        created = events_repository.create_event_from_pulled_event(db, event)
        if created:
            sync_repository.create_pulled_event_tags(db, created, event.tags, user)

            sync_repository.create_pulled_event_reports(
                db, created.uuid, event.event_reports, user
            )
            sync_repository.create_pulled_event_objects(
                db, created.id, event.objects, user
            )
            sync_repository.create_pulled_event_attributes(
                db, created.id, event.attributes, user
            )

            # TODO: publish event creation to RabbitMQ
            logger.info(f"Event {event.uuid} created")
            return created
    else:
        # update event
        if not existing_event.locked and not server.internal:
            logger.warning(
                "Blocked an edit to an event that was created locally. This can happen if a synchronised event that was created on this instance was modified by an administrator on the remote side."
            )
            return False

        # TODO: handle protected event

        # see app/Model/Event::_edit
        if existing_event.distribution == DistributionLevel.SHARING_GROUP:
            if existing_event.sharing_group is None:
                logger.error(
                    "Event could not be saved: Sharing group chosen as the distribution level, but no sharing group specified. Make sure that the event includes a valid sharing_group_id or change to a different distribution level."
                )
                return False

            sharing_group_id = sharing_groups_repository.capture_sharing_group(
                existing_event.sharing_group, user, server
            )

            if sharing_group_id > 0:
                event.sharing_group_id = sharing_group_id
            else:
                event.sharing_group_id = None

        if event.timestamp.timestamp() <= existing_event.timestamp:
            return

        updated = events_repository.update_event_from_pulled_event(
            db, existing_event, event
        )
        if updated:
            sync_repository.create_pulled_event_tags(db, updated, event.tags, server, user)
            sync_repository.create_pulled_event_reports(db, updated.uuid, event.event_reports, server, user)
            sync_repository.update_pulled_event_objects(db, updated.id, event.objects, server, user)
            sync_repository.update_pulled_event_attributes(db, updated.id, event.attributes, server, user)

            # TODO: publish event update to ZMQ
            logger.info("Updated event %s" % event.uuid)
            return updated

    return False


def create_pulled_event_sharing_group(
    db: Session,
    sharing_group: MISPSharingGroup,
    server: server_schemas.Server,
    user: user_models.User,
) -> Union[int, None]:
    """
    see: app/Model/Event.php::__captureObjects()
    """
    sharing_group_id = sharing_groups_repository.capture_sharing_group(
        db, sharing_group, user, server
    )

    if sharing_group_id > 0:
        return sharing_group_id

    return None


def update_server(
    db: Session,
    server_id: int,
    server: server_schemas.ServerUpdate,
) -> server_models.Server:
    # TODO: app/Model/Server.php::beforeValidate() && app/Model/Server.php::$validate
    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    server_patch = server.model_dump(exclude_unset=True)
    for key, value in server_patch.items():
        setattr(db_server, key, value)

    db.add(db_server)
    db.commit()
    db.refresh(db_server)

    return db_server


def delete_server(db: Session, server_id: int) -> None:
    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    db.delete(db_server)
    db.commit()


def test_server_connection(db: Session, server_id: int) -> None:
    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    # get remote instance version
    try:
        remote_misp = get_remote_misp_connection(db_server)

        return server_schemas.TestServerConnectionResponse(
            status="ok",
            version=remote_misp.version.get("version"),
        )

    except Exception as ex:
        return server_schemas.TestServerConnectionResponse(
            status="error",
            error=ex.detail,
        )


def get_remote_events_index(
    db: Session,
    server_id: int,
    limit: int,
    page: int,
    event_info: str = None,
    attribute_value: str = None,
    event_uuid: str = None,
    organisation: str = None,
    tags: str = None,
    threat_level: str = None,
    analysis_level: str = None,
    timestamp_from: str = None,
    timestamp_to: str = None,
):
    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    try:
        remote_misp = get_remote_misp_connection(db_server)

        timestamp = (
            (timestamp_from, timestamp_to)
            if timestamp_from and timestamp_to
            else timestamp_from or timestamp_to
        )

        return remote_misp.search_index(
            published=True,
            limit=limit,
            page=page,
            attribute=attribute_value or None,
            eventinfo=event_info or None,
            timestamp=timestamp or None,
            eventid=event_uuid or None,
            org=organisation or None,
            tags=tags or None,
            threatlevel=threat_level or None,
            analysis=analysis_level or None,
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable: %s" % ex
        )


def get_remote_event_attributes(
    db: Session, server_id: int, event_uuid: str, limit: int, page: int
):

    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    try:
        remote_misp = get_remote_misp_connection(db_server)
    except Exception as ex:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable: %s" % ex
        )

    return remote_misp.search(
        controller="attributes", eventid=event_uuid, with_attachments=True, deleted=["0"], limit=limit, page=page
    )


def get_remote_event_objects(
    db: Session, server_id: int, event_uuid: str, limit: int, page: int
):

    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    try:
        remote_misp = get_remote_misp_connection(db_server)
    except Exception as ex:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable: %s" % ex
        )

    return remote_misp.search(
        controller="objects", eventid=event_uuid, with_attachments=True, deleted=["0"], limit=limit, page=page
    )

def get_remote_event_reports(
    db: Session, server_id: int, event_id: int
):

    db_server = get_server_by_id(db, server_id=server_id)

    if db_server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    try:
        remote_misp = get_remote_misp_connection(db_server)
    except Exception as ex:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable: %s" % ex
        )

    return remote_misp.get_event_reports(event_id)
