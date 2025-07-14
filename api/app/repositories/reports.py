from app.services.opensearch import get_opensearch_client
from app.models import event as event_models
import logging
import uuid
import time
import datetime

logger = logging.getLogger(__name__)


def get_event_reports_by_event_uuid(event_uuid: uuid.UUID):
    OpenSearchClient = get_opensearch_client()

    search_body = {
        "query": {
            "bool": {
                "must": [{"term": {"event_uuid.keyword": str(event_uuid)}}],
                "filter": [{"term": {"deleted": False}}],
            }
        }
    }

    response = OpenSearchClient.search(index="misp-event-reports", body=search_body)

    return response["hits"]["hits"]


def create_event_report(event: event_models.Event, report: dict):
    OpenSearchClient = get_opensearch_client()

    report_uuid = str(uuid.uuid4())
    if report["name"] is None or report["name"] == "":
        report["name"] = f"Event report (%d)" % int(time.time())

    document = {
        "uuid": report_uuid,
        "distribution": event.distribution.value,
        "sharing_group_id": event.sharing_group_id,
        "name": report["name"],
        "content": report["content"],
        "id": None,
        "event_id": event.id,
        "timestamp": int(time.time()),
        "@timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "deleted": False,
        "event_uuid": str(event.uuid),
    }

    response = OpenSearchClient.index(
        index="misp-event-reports", body=document, id=report_uuid
    )

    if response["result"] == "created":
        logger.info(f"Report created for event {event.uuid}")
    else:
        logger.error(f"Failed to create report for event {event.uuid}: {response}")

    return document


def update_event_report(report_uuid: uuid.UUID, report: dict):
    OpenSearchClient = get_opensearch_client()

    search_body = {"query": {"term": {"uuid.keyword": str(report_uuid)}}}
    response = OpenSearchClient.search(index="misp-event-reports", body=search_body)

    if not response["hits"]["hits"]:
        logger.error(f"Report with UUID {report_uuid} not found")
        return None

    document = response["hits"]["hits"][0]["_source"]
    document.update(report)

    response = OpenSearchClient.index(
        index="misp-event-reports", body=document, id=str(report_uuid)
    )

    if response["result"] == "updated":
        logger.info(f"Report {report_uuid} updated successfully")
    else:
        logger.error(f"Failed to update report {report_uuid}: {response}")

    return document


def delete_event_report(report_uuid: uuid.UUID):
    OpenSearchClient = get_opensearch_client()

    search_body = {"query": {"term": {"uuid.keyword": str(report_uuid)}}}
    response = OpenSearchClient.search(index="misp-event-reports", body=search_body)

    if not response["hits"]["hits"]:
        logger.error(f"Report with UUID {report_uuid} not found")
        return None

    document = response["hits"]["hits"][0]["_source"]
    document["deleted"] = True

    response = OpenSearchClient.index(
        index="misp-event-reports", body=document, id=str(report_uuid)
    )

    if response["result"] == "updated":
        logger.info(f"Report {report_uuid} deleted successfully")
    else:
        logger.error(f"Failed to delete report {report_uuid}: {response}")

    return document
