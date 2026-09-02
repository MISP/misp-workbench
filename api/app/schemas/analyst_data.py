import enum
from typing import Any, Optional

from pydantic import BaseModel


class AnalystDataType(str, enum.Enum):
    """
    The three MISP analyst data object types.

    The value doubles as the `object_type` MISP uses when analyst data is
    attached to other analyst data, so a nested note carries
    `object_type="Note"` pointing at its parent's uuid.
    """

    NOTE = "Note"
    OPINION = "Opinion"
    RELATIONSHIP = "Relationship"


# object_type values MISP may attach analyst data to. Anything outside this set
# is still captured -- the list only drives validation of read queries.
ANALYST_DATA_PARENT_TYPES = {
    "Attribute",
    "Event",
    "EventReport",
    "Galaxy",
    "GalaxyCluster",
    "Note",
    "Object",
    "Opinion",
    "Organisation",
    "Relationship",
    "SharingGroup",
}


# ── Response schemas ──────────────────────────────────────────────────────────


class AnalystDataBase(BaseModel):
    uuid: str
    analyst_type: AnalystDataType
    object_uuid: str
    object_type: str
    event_uuid: Optional[str] = None
    authors: Optional[str] = None
    org_uuid: Optional[str] = None
    orgc_uuid: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    distribution: Optional[int] = None
    sharing_group_id: Optional[int] = None
    deleted: bool = False


class Note(AnalystDataBase):
    note: Optional[str] = None
    language: Optional[str] = None
    note_type_name: Optional[str] = None


class Opinion(AnalystDataBase):
    opinion: Optional[int] = None
    comment: Optional[str] = None


class Relationship(AnalystDataBase):
    related_object_uuid: Optional[str] = None
    related_object_type: Optional[str] = None
    relationship_type: Optional[str] = None


class AnalystDataThread(BaseModel):
    """
    One analyst data document plus the analyst data attached to it.

    MISP threads analyst data recursively -- a note can carry notes and
    opinions of its own -- so children are the same shape as their parent.
    """

    uuid: str
    analyst_type: AnalystDataType
    object_uuid: str
    object_type: str
    data: dict[str, Any]
    notes: list["AnalystDataThread"] = []
    opinions: list["AnalystDataThread"] = []
    relationships: list["AnalystDataThread"] = []


AnalystDataThread.model_rebuild()


class AnalystDataListResponse(BaseModel):
    notes: list[AnalystDataThread] = []
    opinions: list[AnalystDataThread] = []
    relationships: list[AnalystDataThread] = []
