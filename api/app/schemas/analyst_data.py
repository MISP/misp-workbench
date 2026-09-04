import enum
from typing import Any, Optional

from pydantic import BaseModel, Field


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


# ── Request schemas ───────────────────────────────────────────────────────────


class AnalystDataCreateBase(BaseModel):
    """
    The parent an analyst data object hangs off. `object_type` is the parent's
    MISP type, so replying to a note means object_type="Note" and the note's
    uuid as object_uuid.
    """

    object_uuid: str
    object_type: str
    distribution: Optional[int] = None
    sharing_group_id: Optional[int] = None


class NoteCreate(AnalystDataCreateBase):
    note: str = Field(min_length=1)
    language: Optional[str] = None
    note_type_name: Optional[str] = None


class OpinionCreate(AnalystDataCreateBase):
    opinion: int = Field(ge=0, le=100)
    comment: str = Field(min_length=1)


class RelationshipCreate(AnalystDataCreateBase):
    related_object_uuid: str
    related_object_type: str
    relationship_type: str = Field(min_length=1)


class AnalystDataUpdate(BaseModel):
    """
    A partial update. Only the fields belonging to the stored object's type are
    applied; anything else is rejected rather than silently dropped.
    """

    note: Optional[str] = Field(default=None, min_length=1)
    language: Optional[str] = None
    note_type_name: Optional[str] = None
    opinion: Optional[int] = Field(default=None, ge=0, le=100)
    comment: Optional[str] = Field(default=None, min_length=1)
    related_object_uuid: Optional[str] = None
    related_object_type: Optional[str] = None
    relationship_type: Optional[str] = Field(default=None, min_length=1)
    distribution: Optional[int] = None
    sharing_group_id: Optional[int] = None


# The fields a caller may set per type, used to reject an update that does not
# belong to the stored object's type.
EDITABLE_FIELDS = {
    AnalystDataType.NOTE: {"note", "language", "note_type_name"},
    AnalystDataType.OPINION: {"opinion", "comment"},
    AnalystDataType.RELATIONSHIP: {
        "related_object_uuid",
        "related_object_type",
        "relationship_type",
    },
}

# Settable on any type.
COMMON_EDITABLE_FIELDS = {"distribution", "sharing_group_id"}
