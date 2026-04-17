DEFAULT_SETTINGS = {
    "correlations": {
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
