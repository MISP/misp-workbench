import enum


class DistributionLevel(enum.Enum):
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


