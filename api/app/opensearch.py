import os

from opensearchpy import OpenSearch

_prod = os.environ.get("ENVIRONMENT", "prod") == "prod"
_username = os.environ.get("OPENSEARCH_USERNAME") or ("admin" if _prod else "")
_password = os.environ.get("OPENSEARCH_PASSWORD") or os.environ.get("OPENSEARCH_INITIAL_ADMIN_PASSWORD", "")
_http_auth = (_username, _password) if _username else None

OpenSearchClient = OpenSearch(
    hosts=[
        {
            "host": os.environ["OPENSEARCH_HOSTNAME"],
            "port": os.environ["OPENSEARCH_PORT"],
        }
    ],
    http_auth=_http_auth,
    use_ssl=_prod,
    verify_certs=False,
    ssl_show_warn=False,
)
