import logging
from hashlib import sha1
from typing import Union

from app.models import event as event_models
from app.models import server as server_models
from app.models import tag as tag_models
from app.models import user as user_models
from app.models.event import DistributionLevel
from app.repositories import attributes as attributes_repository
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
    PyMISP,
)
from sqlalchemy.orm import Session

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
        remote_misp = PyMISP(url=server.url, key=server.authkey, ssl=verify_cert)
        remote_misp_version = remote_misp.misp_instance_version
    except Exception:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable"
        )
    # check sync permissions
    if not remote_misp_version["perm_sync"]:
        raise HTTPException(
            status_code=401, detail="Not authorized to sync from remote MISP instance"
        )

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
        raise HTTPException(
            status_code=501,
            detail="Server pull technique `pull_relevant_clusters` not implemented yet.",
        )

    if technique == "update":
        # TODO implement update server pull technique
        raise HTTPException(
            status_code=501,
            detail="Server pull technique `update` not implemented yet.",
        )

    if technique == "full":
        return pull_server_by_id_full(db, settings, server, remote_misp, user)

    raise HTTPException(
        status_code=400,
        detail="Unknown server pull technique `%s` not implemented yet." % technique,
    )


def pull_server_by_id_full(
    db: Session,
    settings: Settings,
    server: server_schemas.Server,
    remote_misp: PyMISP,
    user: user_models.User,
):

    # get a list of the event_ids on the server
    event_ids = get_event_ids_from_server(server, remote_misp)

    # TODO apply MISP.enableEventBlocklisting / removeBlockedEvents
    # TODO apply MISP.enableOrgBlocklisting / removeBlockedEvents

    # pull each of the events sequentially
    for event_id in event_ids:
        pull_event_by_uuid(db, settings, server, event_id, remote_misp, user)

    return {
        "message": "Pulling server ID: %s" % server.id,
        "technique": "full",
        "event_ids": event_ids,
    }


def get_event_ids_from_server(server: server_schemas.Server, remote_misp: PyMISP):
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
    settings: Settings,
    server: server_schemas.Server,
    event_uuid: str,
    remote_misp: PyMISP,
    user: user_models.User,
):
    """
    see: app/Model/Server.php::__pullEvent()
    """

    # fetch event from remote server
    data = {
        "deleted": [0, 1],
        "excludeGalaxy": 1,
        "includeEventCorrelations": 0,
        "includeFeedCorrelations": 0,
        "includeWarninglistHits": 0,
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

    # TODO: process event reports, see app/Model/Event.php::_add()

    # TODO: process cryptographic keys, see app/Model/Event.php::_add()

    # TODO: process sightings, see app/Model/Event.php::_add()

    # TODO: process tag collection, see app/Model/Event.php::_add()

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

        # process attributes
        if event.attributes:
            for attribute in event.attributes:
                attribute = update_pulled_attribute_before_insert(attribute)

        # process objects
        if event.objects:
            for object in event.objects:
                object = update_pulled_object_before_insert(object)

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
            event.attributes = create_pulled_event_attributes(
                db, created.id, event.attributes, server, user
            )
            event.objects = create_pulled_event_objects(
                db, created.id, event.objects, server, user
            )
            create_pulled_event_tags(db, created, event.tags, server, user)
            create_pulled_attributes_tags(db, created, event.attributes, server, user)
            create_pulled_objects_tags(db, created, event.objects, server, user)

            # TODO: publish event creation to ZMQ
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

        updated = events_repository.update_event_from_pulled_event(
            db, existing_event, event
        )
        if updated:
            update_pulled_event_attributes(db, updated.id, event.attributes, server, user)
            update_pulled_event_objects(db, updated.id, event.objects, server, user)
            create_pulled_event_tags(db, updated, event.tags, server, user)
            # create_pulled_attributes_tags(db, updated, event.attributes, server, user)
            # create_pulled_objects_tags(db, updated, event.objects, server, user)

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


def create_pulled_event_attributes(
    db: Session,
    local_event_id: int,
    attributes: list[MISPAttribute],
    server: server_schemas.Server,
    user: user_models.User,
) -> list[MISPAttribute]:
    """
    see: app/Model/Event.php::_add()
    """

    # TODO: extract this logic somewhere reusable
    hashes_dict = {}
    for attribute in attributes:
        hash = sha1(
            (str(attribute.value) + attribute.type + attribute.category).encode("utf-8")
        ).hexdigest()
        if hash not in hashes_dict:
            # see: app/Model/Attribute.php::captureAttribute()
            local_attribute = (
                attributes_repository.create_attribute_from_pulled_attribute(
                    db, attribute, local_event_id, user
                )
            )
            attribute.event_id = local_event_id
            attribute.id = local_attribute.id

            hashes_dict[hash] = True

    return attributes


def update_pulled_event_attributes(
    db: Session,
    local_event_id: int,
    attributes: list[MISPAttribute],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    """
    see: app/Model/Attribute.php::captureAttribute()
    see: app/Model/Tag.php::captureTag()
    see: app/Model/Tag.php::captureTagWithCache()
    """

    for pulled_attribute in attributes:
        # see: app/Model/Attribute.php::captureAttribute()
        local_attribute = attributes_repository.get_attribute_by_uuid(db, pulled_attribute.uuid)
        
        if local_attribute is None:
            attributes_repository.create_attribute_from_pulled_attribute(
                db, pulled_attribute, local_event_id, user
            )
        else:
            # see: app/Model/Attribute.php::edit()
            attributes_repository.update_attribute_from_pulled_attribute(
                db, local_attribute, pulled_attribute, local_event_id, user
            )
            
def update_pulled_event_objects(
    db: Session,
    local_event_id: int,
    objects: list[MISPObject],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    """
    see: app/Model/MispObject.php::captureObject()
    see: app/Model/MispObject.php::checkForDuplicateObjects()
    """

    for object in objects:
        # see: app/Model/MispObject.php::captureObject()
        local_object = objects_repository.get_object_by_uuid(db, object.uuid)
        
        if local_object is None:
            objects_repository.create_object_from_pulled_object(
                db, object, local_event_id, user
            )
        else:
            # see: app/Model/MispObject.php::edit()
            objects_repository.update_object_from_pulled_object(
                db, local_object, object, local_event_id, user
            )

def create_pulled_event_objects(
    db: Session,
    local_event_id: int,
    objects: list[MISPObject],
    server: server_schemas.Server,
    user: user_models.User,
) -> list[MISPObject]:
    """
    see: app/Model/Event.php::_add()
    """

    for object in objects:
        # see: app/Model/MispObject.php::captureObject()
        # TODO: app/Model/MispObject.php::checkForDuplicateObjects()
        db_object = objects_repository.create_object_from_pulled_object(
            db, object, local_event_id, user
        )
        object.id = db_object.id
        object.event_id = local_event_id

    # see: app/Model/ObjectReference.php::captureReference()

    return objects


def create_pulled_tags(
    db: Session,
    event: event_models.Event,
    pulled_tags: list[MISPTag],
    server: server_schemas.Server,
    user: user_models.User,
) -> list[tag_models.Tag]:
    """
    see: app/Model/Event.php::__captureObjects()
    see: app/Model/Tag.php::captureTag()
    see: app/Model/Tag.php::captureTagWithCache()
    """

    tags = []

    for tag in pulled_tags:
        # TODO: cache capture_tag()
        tag = tags_repository.capture_tag(db, tag, user)
        if tag:
            tags.append(tag)

    return tags


def create_pulled_event_tags(
    db: Session,
    event: event_models.Event,
    pulled_tags: list[MISPTag],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:

    tags = create_pulled_tags(db, event, pulled_tags, server, user)

    # TODO: bulk insert
    for tag in tags:
        tags_repository.tag_event(db, event, tag)


def create_pulled_attributes_tags(
    db: Session,
    event: event_models.Event,
    attributes: list[MISPAttribute],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    """
    see: app/Model/Event.php::__captureObjects()
    see: app/Model/Event.php::__captureAttributeTags()
    see: app/Model/Tag.php::captureTag()
    see: app/Model/Tag.php::captureTagWithCache()
    """

    for attribute in attributes:
        tags = create_pulled_tags(db, event, attribute.tags, server, user)

        # TODO: bulk insert
        for tag in tags:
            tags_repository.tag_attribute(db, attribute, tag)


def create_pulled_objects_tags(
    db: Session,
    event: event_models.Event,
    objects: list[MISPObject],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    """
    see: app/Model/Event.php::__captureObjects()
    see: app/Model/Event.php::__captureAttributeTags()
    see: app/Model/Tag.php::captureTag()
    see: app/Model/Tag.php::captureTagWithCache()
    """

    for object in objects:
        for attribute in object.attributes:
            tags = create_pulled_tags(db, event, attribute.tags, server, user)

            # TODO: bulk insert
            for tag in tags:
                tags_repository.tag_attribute(db, attribute, tag)


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
            attribute=attribute_value,
            eventinfo=event_info,
            timestamp=timestamp,
            eventid=event_uuid,
            org=organisation,
            tags=tags,
            threatlevel=threat_level,
            analysis=analysis_level,
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500, detail="Remote MISP instance not reachable"
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
            status_code=500, detail="Remote MISP instance not reachable"
        )

    return remote_misp.search(
        controller="attributes", eventid=event_uuid, limit=limit, page=page,
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
            status_code=500, detail="Remote MISP instance not reachable"
        )

    return remote_misp.search(
        controller="objects", eventid=event_uuid, limit=limit, page=page
    )
