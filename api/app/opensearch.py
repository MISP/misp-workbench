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

# # Sample data to be indexed
# data = {
#     'title': 'Sample Document',
#     'content': 'This is a sample document to be indexed in OpenSearch.',
#     'author': 'John Doe',
#     'timestamp': '2023-05-24T12:34:56'
# }

# # Index the document
# response = client.index(
#     index="test",
#     id=1,
#     body=data
# )

# # Check the response
# if response['result'] == 'created':
#     print('Document indexed successfully')
# else:
#     print(f'Failed to index document. Result: {response["result"]}')
#     print(response)
