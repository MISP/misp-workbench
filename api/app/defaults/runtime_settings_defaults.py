DEFAULT_SETTINGS = {
    "correlations": {
        # Correlate an attribute in the background as soon as it is created or
        # its value/type/correlation flag changes, instead of waiting for the
        # next full ``generate_correlations`` run.
        "correlateOnChange": True,
        "matchTypes": ["term", "cidr"],
        "maxCorrelationsPerDoc": 1000,
        "prefixLength": 10,
        "minScore": 2,
        "fuzzynessAlgo": "AUTO",
        "possibleCdirAttributeTypes": [
            "ip-src",
            "ip-src|port",
            "ip-dst",
            "ip-dst|port",
            "domain|ip",
        ],
        "opensearchFlushBulkSize": 100,
        # Correlation queries sent to OpenSearch in a single multi-search
        # request. Higher means fewer round trips during bulk ingestion, at the
        # cost of a bigger response held in memory.
        "msearchChunkSize": 25,
    },
    "notifications": {
        # Maximum number of notification emails sent per user per hour.
        # Set to 0 to disable the limit.
        "email_max_per_hour": 10,
    },
    "retention": {
        "enabled": False,
        "period_days": 365,
        "warning_days": 30,
        "exempt_tags": ["retention:exempt"],
    },
}
