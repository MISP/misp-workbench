DEFAULT_SETTINGS = {
    "correlations": {
        # Correlate an attribute in the background as soon as it is created or
        # its value/type/correlation flag changes, instead of waiting for the
        # next full ``generate_correlations`` run.
        "correlateOnChange": True,
        # ``ja4`` matches JA4+ fingerprints exactly, and only with each other.
        "matchTypes": ["term", "cidr", "ja4"],
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
    "exports": {
        # Streaming exports (/attributes/export, /events/export) one user can
        # run at once; each holds an OpenSearch point-in-time context while it
        # streams. Further requests get a 429. Set to 0 to disable the limit.
        "max_concurrent_per_user": 3,
        # Deltas kept per incremental export feed; a consumer further behind
        # than the oldest one has to download the full artifact again.
        "delta_retention": 96,
    },
    "warninglists": {
        # Leave attributes on an enabled warninglist out of exports, feeds and
        # lookup by default (each can still ask for them). restSearch follows
        # MISP and only filters when enforceWarninglist is passed; sinks have
        # their own per-sink switch.
        "enforce_on_outputs": True,
    },
    "sightings": {
        # Turn to_ids off on every attribute holding a value once this many
        # distinct organisations have reported it as a false positive (MISP
        # sighting type 1), so SIEMs stop alerting on it. 0 disables it.
        "false_positive_threshold": 0,
    },
    "retention": {
        "enabled": False,
        "period_days": 365,
        "warning_days": 30,
        "exempt_tags": ["retention:exempt"],
    },
}
