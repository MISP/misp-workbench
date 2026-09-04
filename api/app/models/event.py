import enum


# IntEnum, deliberately. pymisp hands back plain ints and the Pydantic event
# schemas hold ints under `use_enum_values`, so a plain Enum member never
# compared equal to either: comparisons against it were silently always False,
# which left the pull time distribution downgrade, the sharing group capture on
# event update and the empty event guard all dead code. IntEnum also makes
# int() and json.dumps() work on a member, both of which raised before.
#
# It does not help with the *strings* MISP's JSON carries ("2"), which still
# need normalising -- see servers.py::distribution_is.
class DistributionLevel(enum.IntEnum):
    """
    Enum for the Event distribution level
    """

    ORGANISATION_ONLY = 0
    COMMUNITY_ONLY = 1
    CONNECTED_COMMUNITIES = 2
    ALL_COMMUNITIES = 3
    SHARING_GROUP = 4
    INHERIT_EVENT = 5


class ThreatLevel(enum.Enum):
    """
    Enum for the Event threat level
    """

    HIGH = 1
    MEDIUM = 2
    LOW = 3
    UNDEFINED = 4


class AnalysisLevel(enum.Enum):
    """
    Enum for the Event analysis level
    """

    INITIAL = 0
    ONGOING = 1
    COMPLETE = 2
