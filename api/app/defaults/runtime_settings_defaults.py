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
    "sinks": {
        # Sends from notebooks and reactor scripts one user may make per
        # minute (each up to 10,000 attributes or records). 0 disables it.
        "sends_per_minute": 30,
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
    "scoring": {
        # A confidence score (0-100) on every consolidated indicator, from its
        # sources, age, sightings and warninglist hits. Outputs can filter on
        # it (score:>=N, min_score, restSearch excludeDecayed).
        "enabled": True,
        # Starting score by the best source the indicator comes from.
        "base_by_source": {"local": 70, "server": 60, "feed": 50, "unknown": 50},
        # Added per further independent source, up to the max.
        "corroboration_per_source": 5,
        "corroboration_max": 15,
        # Days for the score to halve, counted from last_seen; 0 never decays.
        # Types not listed use default_half_life_days.
        "half_life_days": {
            "ip-src": 30,
            "ip-dst": 30,
            "ip-src|port": 30,
            "ip-dst|port": 30,
            "domain|ip": 30,
            "url": 30,
            "uri": 30,
            "domain": 90,
            "hostname": 90,
            "email": 90,
            "email-src": 90,
            "email-dst": 90,
            "md5": 0,
            "sha1": 0,
            "sha224": 0,
            "sha256": 0,
            "sha384": 0,
            "sha512": 0,
            "ssdeep": 0,
            "imphash": 0,
            "tlsh": 0,
            "filename|md5": 0,
            "filename|sha1": 0,
            "filename|sha256": 0,
            "malware-sample": 0,
        },
        "default_half_life_days": 180,
        # Positive sightings add up to this much (5 for one, 10 for three,
        # 15 for seven).
        "sighting_boost_max": 15,
        # Taken off per false-positive sighting, up to the max.
        "false_positive_penalty": 20,
        "false_positive_penalty_max": 60,
        # On an enabled warninglist.
        "warninglist_penalty": 50,
        # An expiration sighting newer than any positive one caps the score.
        "expiration_cap": 10,
        # Below this an indicator counts as decayed (restSearch excludeDecayed).
        "decayed_below": 30,
        # A stored score is rewritten when it moves this much, or crosses
        # decayed_below: hourly decay doesn't rewrite every indicator.
        "refresh_step": 5,
    },
    "retention": {
        "enabled": False,
        "period_days": 365,
        "warning_days": 30,
        "exempt_tags": ["retention:exempt"],
    },
}
