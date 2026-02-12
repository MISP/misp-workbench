from enum import Enum
from typing import Optional
from uuid import UUID

from app.models.event import DistributionLevel
from app.schemas.tag import Tag
from pydantic import BaseModel, ConfigDict


class AttributeBase(BaseModel):
    event_id: Optional[int] = None
    object_id: Optional[int] = None
    event_uuid: Optional[UUID] = None
    object_relation: Optional[str] = None
    category: str
    type: str
    value: str
    to_ids: Optional[bool] = None
    uuid: Optional[UUID] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    disable_correlation: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    model_config = ConfigDict(use_enum_values=True)


class Attribute(AttributeBase):
    id: int
    tags: list[Tag] = []
    correlations: list[dict] = None
    model_config = ConfigDict(from_attributes=True)


class AttributeCreate(AttributeBase):
    pass


class AttributeUpdate(BaseModel):
    object_id: Optional[int] = None
    object_relation: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None
    to_ids: Optional[bool] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    comment: Optional[str] = None
    deleted: Optional[bool] = None
    disable_correlation: Optional[bool] = None
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None

class AttributeType(str, Enum):
    TEXT = "text"
    LINK = "link"
    COMMENT = "comment"
    OTHER = "other"
    HEX = "hex"
    ANONYMIZED = "anonymised"
    GIT_COMMIT_ID = "git-commit-id"
    TARGET_USER = "target-user"
    TARGET_EMAIL = "target-email"
    TARGET_MACHINE = "target-machine"
    TARGET_ORG = "target-org"
    TARGET_LOCATION = "target-location"
    TARGET_EXTERNAL = "target-external"
    ATTACHMENT = "attachment"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA224 = "sha224"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA512_224 = "sha512/224"
    SHA512_256 = "sha512/256"
    SHA3_224 = "sha3-224"
    SHA3_256 = "sha3-256"
    SHA3_384 = "sha3-384"
    SHA3_512 = "sha3-512"
    SSDEEP = "ssdeep"
    IMPHASH = "imphash"
    TELFHASH = "telfhash"
    IMPFUZZY = "impfuzzy"
    AUTHENTIHASH = "authentihash"
    VHASH = "vhash"
    PEHASH = "pehash"
    TLSH = "tlsh"
    CDHASH = "cdhash"
    FILENAME = "filename"
    FILENAME_MD5 = "filename|md5"
    FILENAME_SHA1 = "filename|sha1"
    FILENAME_SHA224 = "filename|sha224"
    FILENAME_SHA256 = "filename|sha256"
    FILENAME_SHA384 = "filename|sha384"
    FILENAME_SHA512 = "filename|sha512"
    FILENAME_SHA512_224 = "filename|sha512/224"
    FILENAME_SHA512_256 = "filename|sha512/256"
    FILENAME_SHA3_224 = "filename|sha3-224"
    FILENAME_SHA3_256 = "filename|sha3-256"
    FILENAME_SHA3_384 = "filename|sha3-384"
    FILENAME_SHA3_512 = "filename|sha3-512"
    FILENAME_AUTHENTIHASH = "filename|authentihash"
    FILENAME_VHASH = "filename|vhash"
    FILENAME_SSDEEP = "filename|ssdeep"
    FILENAME_TLSH = "filename|tlsh"
    FILENAME_IMPHASH = "filename|imphash"
    FILENAME_IMPFUZZY = "filename|impfuzzy"
    FILENAME_PEHASH = "filename|pehash"
    MAC_ADDRESS = "mac-address"
    MAC_EUI_64 = "mac-eui-64"
    IP_SRC = "ip-src"
    IP_DST = "ip-dst"
    IP_DST_PORT = "ip-dst|port"
    IP_SRC_PORT = "ip-src|port"
    HOSTNAME = "hostname"
    DOMAIN = "domain"
    EMAIL = "email"
    EMAIL_SRC = "email-src"
    EMAIL_DST = "email-dst"
    EMAIL_SUBJECT = "email-subject"
    EMAIL_ATTACHMENT = "email-attachment"
    EMAIL_BODY = "email-body"
    URL = "url"
    USER_AGENT = "user-agent"
    AS = "AS"
    PATTERN_IN_FILE = "pattern-in-file"
    PATTERN_IN_TRAFFIC = "pattern-in-traffic"
    FILENAME_PATTERN = "filename-pattern"
    STIX2_PATTERN = "stix2-pattern"
    YARA = "yara"
    SIGMA = "sigma"
    MIME_TYPE = "mime-type"
    MALWARE_SAMPLE = "malware-sample"
    MALWARE_TYPE = "malware-type"
    VULNERABILITY = "vulnerability"
    CPE = "cpe"
    WEAKNESS = "weakness"
    X509_FINGERPRINT_SHA1 = "x509-fingerprint-sha1"
    X509_FINGERPRINT_MD5 = "x509-fingerprint-md5"
    X509_FINGERPRINT_SHA256 = "x509-fingerprint-sha256"
    JA3_FINGERPRINT_MD5 = "ja3-fingerprint-md5"
    JARM_FINGERPRINT = "jarm-fingerprint"
    HASSH_MD5 = "hassh-md5"
    HASSHSERVER_MD5 = "hasshserver-md5"
    HOSTNAME_PORT = "hostname|port"
    EMAIL_DST_DISPLAY_NAME = "email-dst-display-name"
    EMAIL_SRC_DISPLAY_NAME = "email-src-display-name"
    EMAIL_HEADER = "email-header"
    EMAIL_REPLY_TO = "email-reply-to"
    EMAIL_X_MAILER = "email-x-mailer"
    EMAIL_MIME_BOUNDARY = "email-mime-boundary"
    EMAIL_THREAD_INDEX = "email-thread-index"
    EMAIL_MESSAGE_ID = "email-message-id"
    MOBILE_APPLICATION_ID = "mobile-application-id"
    CHROME_EXTENSION_ID = "chrome-extension-id"
    WHOIS_REGISTRANT_EMAIL = "whois-registrant-email"
    REGKEY = "regkey"
    REGKEY_VALUE = "regkey|value"
    PATTERN_IN_MEMORY = "pattern-in-memory"
    PDB = "pdb"
    NAMED_PIPE = "named pipe"
    MUTEX = "mutex"
    PROCESS_STATE = "process-state"
    WINDOWS_SCHEDULED_TASK = "windows-scheduled-task"
    WINDOWS_SERVICE_NAME = "windows-service-name"
    WINDOWS_SERVICE_DISPLAYNAME = "windows-service-displayname"
    COOKIE = "cookie"
    GENE = "gene"
    KUSTO_QUERY = "kusto-query"
    PGP_PUBLIC_KEY = "pgp-public-key"
    PGP_PRIVATE_KEY = "pgp-private-key"
    PORT = "port"
    DOMAIN_IP = "domain|ip"
    EPPN = "eppn"
    URI = "uri"
    HTTP_METHOD = "http-method"
    SNORT = "snort"
    BRO = "bro"
    ZEEK = "zeek"
    COMMUNITY_ID = "community-id"
    FAVICON_MMH3 = "favicon-mmh3"
    DKIM = "dkim"
    DKIM_SIGNATURE = "dkim-signature"
    SSH_FINGERPRINT = "ssh-fingerprint"
    THREAT_ACTOR = "threat-actor"
    CAMPAIGN_NAME = "campaign-name"
    CAMPAIGN_ID = "campaign-id"
    WHOIS_REGISTRANT_PHONE = "whois-registrant-phone"
    WHOIS_REGISTRANT_NAME = "whois-registrant-name"
    WHOIS_REGISTRANT_ORG = "whois-registrant-org"
    WHOIS_REGISTRAR = "whois-registrar"
    WHOIS_CREATION_DATE = "whois-creation-date"
    DNS_SOA_EMAIL = "dns-soa-email"
    GITHUB_REPOSITORY = "github-repository"
    CORTEX = "cortex"
    BTC = "btc"
    DASH = "dash"
    XMR = "xmr"
    IBAN = "iban"
    BIC = "bic"
    BANK_ACCOUNT_NR = "bank-account-nr"
    ABA_RTN = "aba-rtn"
    BIN = "bin"
    CC_NUMBER = "cc-number"
    PRTN = "prtn"
    PHONE_NUMBER = "phone-number"
    GITHUB_USERNAME = "github-username"
    GITHUB_ORGANISATION = "github-organisation"
    JABBER_ID = "jabber-id"
    TWITTER_ID = "twitter-id"
    FIRST_NAME = "first-name"
    MIDDLE_NAME = "middle-name"
    LAST_NAME = "last-name"
    FULL_NAME = "full-name"
    DATE_OF_BIRTH = "date-of-birth"
    PLACE_OF_BIRTH = "place-of-birth"
    GENDER = "gender"
    PASSPORT_NUMBER = "passport-number"
    PASSPORT_COUNTRY = "passport-country"
    PASSPORT_EXPIRATION = "passport-expiration"
    REDRESS_NUMBER = "redress-number"
    NATIONALITY = "nationality"
    VISA_NUMBER = "visa-number"
    ISSUE_DATE_OF_THE_VISA = "issue-date-of-the-visa"
    PRIMARY_RESIDENCE = "primary-residence"
    COUNTRY_OF_RESIDENCE = "country-of-residence"
    SPECIAL_SERVICE_REQUEST = "special-service-request"
    FREQUENT_FLYER_NUMBER = "frequent-flyer-number"
    TRAVEL_DETAILS = "travel-details"
    PAYMENT_DETAILS = "payment-details"
    PLACE_PORT_OF_ORIGINAL_EMBARKATION = "place-port-of-original-embarkation"
    PLACE_PORT_OF_CLEARANCE = "place-port-of-clearance"
    PLACE_PORT_OF_ONWARD_FOREIGN_DESTINATION = "place-port-of-onward-foreign-destination"
    PASSENGER_NAME_RECORD_LOCATOR_NUMBER = "passenger-name-record-locator-number"
    IDENTITY_CARD_NUMBER = "identity-card-number"
    SIZE_IN_BYTES = "size-in-bytes"
    COUNTER = "counter"
    DATETIME = "datetime"
    FLOAT = "float"
    BOOLEAN = "boolean"