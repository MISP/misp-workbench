import logging
from hashlib import sha1
from typing import Union

from app.models import server as server_models
from app.models import user as user_models
from app.models.event import DistributionLevel
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import objects as objects_repository
from app.repositories import users as users_repository
from app.schemas import server as server_schemas
from app.settings import Settings
from fastapi import HTTPException
from pymisp import MISPAttribute, MISPEvent, MISPObject, PyMISP
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
        lastpulledid=server.lastpulledid,
        lastpushedid=server.lastpushedid,
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
        pull_event_by_id(db, settings, server, event_id, remote_misp, user)

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


def pull_event_by_id(
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

    # TODO: save EventTag, see Event::_add()

    # TODO: process event reports, see Event::_add()

    # TODO: process cryptographic keys, see Event::_add()

    # TODO: process sightings, see Event::_add()

    # TODO: process tag collection, see Event::_add()

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
    see: app/Model/Event::_add()
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

    # these transformations come from app/Model/Event::_add()
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

    # TODO: handle user after auth is implemented
    event.user_id = users_repository.get_users(db, limit=1)[0].id

    return event


def update_pulled_attribute_before_insert(attribute: MISPAttribute) -> MISPAttribute:
    # TODO: handle MISP.enable_synchronisation_filtering_on_type / attributes pullRules

    attribute.distribution = downgrade_distribution(attribute.distribution)

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

        created = events_repository.create_event_from_pulled_event(db, event)
        if created:
            create_pulled_event_attributes(
                db, created.id, event.attributes, server, user
            )
            create_pulled_event_objects(db, created.id, event.objects, server, user)

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

        # TODO: see Event::_edit
        updated = events_repository.update_event_from_pulled_event(
            db, existing_event, event
        )
        if updated:
            # TODO: process attribute updates
            # TODO: process object updates
            # TODO: publish event update to ZMQ
            logger.info("Updated event %s" % event.uuid)
            return updated

    return False


def create_pulled_event_attributes(
    db: Session,
    local_event_id: int,
    attributes: list[MISPAttribute],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
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
            # see: Attribute::captureAttribute()
            attributes_repository.create_attribute_from_pulled_attribute(
                db, attribute, local_event_id
            )
            hashes_dict[hash] = True


def create_pulled_event_objects(
    db: Session,
    local_event_id: int,
    objects: list[MISPObject],
    server: server_schemas.Server,
    user: user_models.User,
) -> None:
    """
    see: app/Model/Event.php::_add()
    """

    for object in objects:
        # see: MispObject::captureObject()
        # TODO: MispObject::checkForDuplicateObjects()
        objects_repository.create_object_from_pulled_object(db, object, local_event_id)

    # see: ObjectReference::captureReference()
