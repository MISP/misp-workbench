import os

from opensearchpy import OpenSearch

OpenSearchClient = OpenSearch(
    hosts=[
        {
            "host": os.environ["OPENSEARCH_HOSTNAME"],
            "port": os.environ["OPENSEARCH_PORT"],
        }
    ],
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False,
)
