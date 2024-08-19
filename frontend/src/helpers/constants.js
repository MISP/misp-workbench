export const DISTRIBUTION_LEVEL = {
  ORGANISATION_ONLY: 0,
  COMMUNITY_ONLY: 1,
  CONNECTED_COMMUNITIES: 2,
  ALL_COMMUNITIES: 3,
  SHARING_GROUP: 4,
  INHERIT_EVENT: 5
};

export const THREAT_LEVEL = {
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  UNDEFINED: 4,
};

export const ANALYSIS_LEVEL = {
  INITIAL: 1,
  ONGOING: 2,
  COMPLETE: 3,
};

export const OBJECT_META_CATEGORIES = {
  "network": {
    "description": "Network related objects",
    "templates": [
      "domain", "domain|ip", "domain|whois", "domain|ip|port", "domain|port", "domain|ip|hostname", "domain|hostname", "domain|ip|hostname|port", "domain|ip|port", "domain|port", "domain|ip|port"
    ]
  }
};


export const ATTRIBUTE_TYPES = ["text", "link", "comment", "other", "hex", "anonymised", "git-commit-id", "target-user", "target-email", "target-machine", "target-org", "target-location", "target-external", "attachment", "md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha512/224", "sha512/256", "sha3-224", "sha3-256", "sha3-384", "sha3-512", "ssdeep", "imphash", "telfhash", "impfuzzy", "authentihash", "vhash", "pehash", "tlsh", "cdhash", "filename", "filename|md5", "filename|sha1", "filename|sha224", "filename|sha256", "filename|sha384", "filename|sha512", "filename|sha512/224", "filename|sha512/256", "filename|sha3-224", "filename|sha3-256", "filename|sha3-384", "filename|sha3-512", "filename|authentihash", "filename|vhash", "filename|ssdeep", "filename|tlsh", "filename|imphash", "filename|impfuzzy", "filename|pehash", "mac-address", "mac-eui-64", "ip-src", "ip-dst", "ip-dst|port", "ip-src|port", "hostname", "domain", "email", "email-src", "email-dst", "email-subject", "email-attachment", "email-body", "url", "user-agent", "AS", "pattern-in-file", "pattern-in-traffic", "filename-pattern", "stix2-pattern", "yara", "sigma", "mime-type", "malware-sample", "malware-type", "vulnerability", "cpe", "weakness", "x509-fingerprint-sha1", "x509-fingerprint-md5", "x509-fingerprint-sha256", "ja3-fingerprint-md5", "jarm-fingerprint", "hassh-md5", "hasshserver-md5", "hostname|port", "email-dst-display-name", "email-src-display-name", "email-header", "email-reply-to", "email-x-mailer", "email-mime-boundary", "email-thread-index", "email-message-id", "mobile-application-id", "chrome-extension-id", "whois-registrant-email", "regkey", "regkey|value", "pattern-in-memory", "pdb", "named pipe", "mutex", "process-state", "windows-scheduled-task", "windows-service-name", "windows-service-displayname", "cookie", "gene", "kusto-query", "pgp-public-key", "pgp-private-key", "port", "domain|ip", "eppn", "uri", "http-method", "snort", "bro", "zeek", "community-id", "favicon-mmh3", "dkim", "dkim-signature", "ssh-fingerprint", "threat-actor", "campaign-name", "campaign-id", "whois-registrant-phone", "whois-registrant-name", "whois-registrant-org", "whois-registrar", "whois-creation-date", "dns-soa-email", "github-repository", "cortex", "btc", "dash", "xmr", "iban", "bic", "bank-account-nr", "aba-rtn", "bin", "cc-number", "prtn", "phone-number", "github-username", "github-organisation", "jabber-id", "twitter-id", "first-name", "middle-name", "last-name", "full-name", "date-of-birth", "place-of-birth", "gender", "passport-number", "passport-country", "passport-expiration", "redress-number", "nationality", "visa-number", "issue-date-of-the-visa", "primary-residence", "country-of-residence", "special-service-request", "frequent-flyer-number", "travel-details", "payment-details", "place-port-of-original-embarkation", "place-port-of-clearance", "place-port-of-onward-foreign-destination", "passenger-name-record-locator-number", "identity-card-number", "size-in-bytes", "counter", "datetime", "float", "boolean"];

export const ATTRIBUTE_CATEGORIES = {
  "Internal reference": {
    "description": "Reference used by the publishing party (e.g. ticket number)",
    "types": [
      "text", "link", "comment", "other", "hex", "anonymised", "git-commit-id"
    ]
  },
  "Targeting data": {
    "description": "Internal Attack Targeting and Compromise Information",
    "help": "Targeting information to include recipient email, infected machines, department, and or locations.",
    "types": [
      "target-user", "target-email", "target-machine", "target-org", "target-location", "target-external", "comment", "anonymised"
    ],
  },
  "Antivirus detection": {
    "description": "All the info about how the malware is detected by the antivirus products",
    "help": "List of anti-virus vendors detecting the malware or information on detection performance (e.g. 13/43 or 67%). Attachment with list of detection or link to VirusTotal could be placed here as well.",
    "types": ['link', 'comment', 'text', 'hex', 'attachment', 'other', 'anonymised']
  },
  "Payload delivery": {
    "description": "Information about how the malware is delivered",
    "help": "Information about the way the malware payload is initially delivered, for example information about the email or web-site, vulnerability used, originating IP etc. Malware sample itself should be attached here.",
    "types": ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'sha512/224', 'sha512/256', 'sha3-224', 'sha3-256', 'sha3-384', 'sha3-512', 'ssdeep', 'imphash', 'telfhash', 'impfuzzy', 'authentihash', 'vhash', 'pehash', 'tlsh', 'cdhash', 'filename', 'filename|md5', 'filename|sha1', 'filename|sha224', 'filename|sha256', 'filename|sha384', 'filename|sha512', 'filename|sha512/224', 'filename|sha512/256', 'filename|sha3-224', 'filename|sha3-256', 'filename|sha3-384', 'filename|sha3-512', 'filename|authentihash', 'filename|vhash', 'filename|ssdeep', 'filename|tlsh', 'filename|imphash', 'filename|impfuzzy', 'filename|pehash', 'mac-address', 'mac-eui-64', 'ip-src', 'ip-dst', 'ip-dst|port', 'ip-src|port', 'hostname', 'domain', 'email', 'email-src', 'email-dst', 'email-subject', 'email-attachment', 'email-body', 'url', 'user-agent', 'AS', 'pattern-in-file', 'pattern-in-traffic', 'filename-pattern', 'stix2-pattern', 'yara', 'sigma', 'mime-type', 'attachment', 'malware-sample', 'link', 'malware-type', 'comment', 'text', 'hex', 'vulnerability', 'cpe', 'weakness', 'x509-fingerprint-sha1', 'x509-fingerprint-md5', 'x509-fingerprint-sha256', 'ja3-fingerprint-md5', 'jarm-fingerprint', 'hassh-md5', 'hasshserver-md5', 'other', 'hostname|port', 'email-dst-display-name', 'email-src-display-name', 'email-header', 'email-reply-to', 'email-x-mailer', 'email-mime-boundary', 'email-thread-index', 'email-message-id', 'mobile-application-id', 'chrome-extension-id', 'whois-registrant-email', 'anonymised']
  },
  "Artifacts dropped": {
    "description": "Any artifact (files, registry keys etc.) dropped by the malware or other modifications to the system",
    "help": "",
    "types": ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'sha512/224', 'sha512/256', 'sha3-224', 'sha3-256', 'sha3-384', 'sha3-512', 'ssdeep', 'imphash', 'telfhash', 'impfuzzy', 'authentihash', 'vhash', 'cdhash', 'filename', 'filename|md5', 'filename|sha1', 'filename|sha224', 'filename|sha256', 'filename|sha384', 'filename|sha512', 'filename|sha512/224', 'filename|sha512/256', 'filename|sha3-224', 'filename|sha3-256', 'filename|sha3-384', 'filename|sha3-512', 'filename|authentihash', 'filename|vhash', 'filename|ssdeep', 'filename|tlsh', 'filename|imphash', 'filename|impfuzzy', 'filename|pehash', 'regkey', 'regkey|value', 'pattern-in-file', 'pattern-in-memory', 'filename-pattern', 'pdb', 'stix2-pattern', 'yara', 'sigma', 'attachment', 'malware-sample', 'named pipe', 'mutex', 'process-state', 'windows-scheduled-task', 'windows-service-name', 'windows-service-displayname', 'comment', 'text', 'hex', 'x509-fingerprint-sha1', 'x509-fingerprint-md5', 'x509-fingerprint-sha256', 'other', 'cookie', 'gene', 'kusto-query', 'mime-type', 'anonymised', 'pgp-public-key', 'pgp-private-key']
  },
  "Payload installation": {
    "description": "Info on where the malware gets installed in the system",
    "help": "Location where the payload was placed in the system and the way it was installed. For example, a filename|md5 type attribute can be added here like this: c:\\windows\\system32\\malicious.exe|41d8cd98f00b204e9800998ecf8427e.",
    "types": ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'sha512/224', 'sha512/256', 'sha3-224', 'sha3-256', 'sha3-384', 'sha3-512', 'ssdeep', 'imphash', 'telfhash', 'impfuzzy', 'authentihash', 'vhash', 'pehash', 'tlsh', 'cdhash', 'filename', 'filename|md5', 'filename|sha1', 'filename|sha224', 'filename|sha256', 'filename|sha384', 'filename|sha512', 'filename|sha512/224', 'filename|sha512/256', 'filename|sha3-224', 'filename|sha3-256', 'filename|sha3-384', 'filename|sha3-512', 'filename|authentihash', 'filename|vhash', 'filename|ssdeep', 'filename|tlsh', 'filename|imphash', 'filename|impfuzzy', 'filename|pehash', 'pattern-in-file', 'pattern-in-traffic', 'pattern-in-memory', 'filename-pattern', 'stix2-pattern', 'yara', 'sigma', 'vulnerability', 'cpe', 'weakness', 'attachment', 'malware-sample', 'malware-type', 'comment', 'text', 'hex', 'x509-fingerprint-sha1', 'x509-fingerprint-md5', 'x509-fingerprint-sha256', 'mobile-application-id', 'chrome-extension-id', 'other', 'mime-type', 'anonymised']
  },
  "Persistence mechanism": {
    "description": "Mechanisms used by the malware to start at boot",
    "help": "Mechanisms used by the malware to start at boot. This could be a registry key, legitimate driver modification, LNK file in startup",
    "types": ['filename', 'regkey', 'regkey|value', 'comment', 'text', 'other', 'hex', 'anonymised']
  },
  "Network activity": {
    "description": "Information about network traffic generated by the malware",
    "help": "",
    "types": ['ip-src', 'ip-dst', 'ip-dst|port', 'ip-src|port', 'port', 'hostname', 'domain', 'domain|ip', 'mac-address', 'mac-eui-64', 'email', 'email-dst', 'email-src', 'eppn', 'url', 'uri', 'user-agent', 'http-method', 'AS', 'snort', 'pattern-in-file', 'filename-pattern', 'stix2-pattern', 'pattern-in-traffic', 'attachment', 'comment', 'text', 'x509-fingerprint-md5', 'x509-fingerprint-sha1', 'x509-fingerprint-sha256', 'ja3-fingerprint-md5', 'jarm-fingerprint', 'hassh-md5', 'hasshserver-md5', 'other', 'hex', 'cookie', 'hostname|port', 'bro', 'zeek', 'anonymised', 'community-id', 'email-subject', 'favicon-mmh3', 'dkim', 'dkim-signature', 'ssh-fingerprint']
  },
  "Payload type": {
    "description": "Information about the final payload(s)",
    "help": "Information about the final payload(s). Can contain a function of the payload, e.g. keylogger, RAT, or a name if identified, such as Poison Ivy.",
    "types": ['comment', 'text', 'other', 'anonymised']
  },
  "Attribution": {
    "description": "Identification of the group, organisation, or country behind the attack",
    "help": "",
    "types": ['threat-actor', 'campaign-name', 'campaign-id', 'whois-registrant-phone', 'whois-registrant-email', 'whois-registrant-name', 'whois-registrant-org', 'whois-registrar', 'whois-creation-date', 'comment', 'text', 'x509-fingerprint-sha1', 'x509-fingerprint-md5', 'x509-fingerprint-sha256', 'other', 'dns-soa-email', 'anonymised', 'email']
  },
  "External analysis": {
    "description": "Any other result from additional analysis of the malware like tools output",
    "help": "Any other result from additional analysis of the malware like tools output Examples: pdf-parser output, automated sandbox analysis, reverse engineering report.",
    "types": ['md5', 'sha1', 'sha256', 'sha3-224', 'sha3-256', 'sha3-384', 'sha3-512', 'filename', 'filename|md5', 'filename|sha1', 'filename|sha256', 'filename|sha3-224', 'filename|sha3-256', 'filename|sha3-384', 'filename|sha3-512', 'ip-src', 'ip-dst', 'ip-dst|port', 'ip-src|port', 'mac-address', 'mac-eui-64', 'hostname', 'domain', 'domain|ip', 'url', 'user-agent', 'regkey', 'regkey|value', 'AS', 'snort', 'bro', 'zeek', 'pattern-in-file', 'pattern-in-traffic', 'pattern-in-memory', 'filename-pattern', 'vulnerability', 'cpe', 'weakness', 'attachment', 'malware-sample', 'link', 'comment', 'text', 'x509-fingerprint-sha1', 'x509-fingerprint-md5', 'x509-fingerprint-sha256', 'ja3-fingerprint-md5', 'jarm-fingerprint', 'hassh-md5', 'hasshserver-md5', 'github-repository', 'other', 'cortex', 'anonymised', 'community-id']
  },
  "Financial fraud": {
    "description": "Financial Fraud indicators",
    "help": "Financial Fraud indicators, for example: IBAN Numbers, BIC codes, Credit card numbers, etc.",
    "types": ['btc', 'dash', 'xmr', 'iban', 'bic', 'bank-account-nr', 'aba-rtn', 'bin', 'cc-number', 'prtn', 'phone-number', 'comment', 'text', 'other', 'hex', 'anonymised']
  },
  "Support Tool": {
    "description": "Tools supporting analysis or detection of the event",
    "help": "",
    "types": ['link', 'text', 'attachment', 'comment', 'other', 'hex', 'anonymised']
  },
  "Social network": {
    "description": "Social networks and platforms",
    "help": "",
    "types": ['github-username', 'github-repository', 'github-organisation', 'jabber-id', 'twitter-id', 'email', 'email-src', 'email-dst', 'eppn', 'comment', 'text', 'other', 'whois-registrant-email', 'anonymised', 'pgp-public-key', 'pgp-private-key']
  },
  "Person": {
    "description": "A human being - natural person",
    "help": "",
    "types": ['first-name', 'middle-name', 'last-name', 'full-name', 'date-of-birth', 'place-of-birth', 'gender', 'passport-number', 'passport-country', 'passport-expiration', 'redress-number', 'nationality', 'visa-number', 'issue-date-of-the-visa', 'primary-residence', 'country-of-residence', 'special-service-request', 'frequent-flyer-number', 'travel-details', 'payment-details', 'place-port-of-original-embarkation', 'place-port-of-clearance', 'place-port-of-onward-foreign-destination', 'passenger-name-record-locator-number', 'comment', 'text', 'other', 'phone-number', 'identity-card-number', 'anonymised', 'email', 'pgp-public-key', 'pgp-private-key']
  },
  "Other": {
    "description": "Attributes that are not part of any other category or are meant to be used as a component in MISP objects in the future",
    "help": "",
    "types": ATTRIBUTE_TYPES
  },
};
