from app.dependencies import get_opensearch_client
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def get_event_reports_by_event_uuid(event_uuid: UUID):
    OpenSearchClient = get_opensearch_client()

    search_body = {"query": {"term": {"event_uuid.keyword": event_uuid}}}

    response = OpenSearchClient.search(index="misp-event-reports", body=search_body)

    return response["hits"]["hits"]
