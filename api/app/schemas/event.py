from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.event import AnalysisLevel, DistributionLevel, ThreatLevel
from app.schemas.attribute import Attribute
from app.schemas.object import Object
from app.schemas.sharing_groups import SharingGroup
from app.schemas.tag import Tag
from app.schemas.organisations import Organisation
from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    org_id: Optional[int] = None
    date: Optional[datetime] = None
    info: str
    user_id: Optional[int] = None
    uuid: Optional[UUID] = None
    published: Optional[bool] = None
    analysis: Optional[AnalysisLevel] = None
    attribute_count: Optional[int] = None
    object_count: Optional[int] = None
    orgc_id: Optional[int] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    proposal_email_lock: Optional[bool] = None
    locked: Optional[bool] = None
    threat_level: Optional[ThreatLevel] = None
    publish_timestamp: Optional[int] = None
    sighting_timestamp: Optional[int] = None
    disable_correlation: Optional[bool] = None
    extends_uuid: Optional[UUID] = None
    protected: Optional[bool] = None
    deleted: Optional[bool] = None
    model_config = ConfigDict(use_enum_values=True)


class Event(EventBase):
    attributes: list[Attribute] = []
    objects: list[Object] = []
    sharing_group: Optional[SharingGroup] = None
    tags: list[Tag] = []
    organisation: Optional[Organisation] = None
    model_config = ConfigDict(from_attributes=True)

    def to_misp_format(self) -> dict:
        event_json = {
            "uuid": str(self.uuid) if self.uuid else None,
            "info": self.info,
            "published": self.published,
            "analysis": self.analysis,
            "distribution": self.distribution,
            "sharing_group_id": self.sharing_group_id,
            "timestamp": self.timestamp,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "threat_level_id": self.threat_level,
            "publish_timestamp": self.publish_timestamp,
            "sighting_timestamp": self.sighting_timestamp,
            "disable_correlation": self.disable_correlation,
            "extends_uuid": str(self.extends_uuid) if self.extends_uuid else None,
            "Attribute": [attr.to_misp_format() for attr in self.attributes],
            "Object": [obj.to_misp_format() for obj in self.objects],
            "Tag": [tag.model_dump() for tag in self.tags],
        }

        if self.organisation:
            event_json["Orgc"] = self.organisation.model_dump()

        return {"Event": event_json}


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    date: Optional[datetime] = None
    info: Optional[str] = None
    published: Optional[bool] = None
    analysis: Optional[AnalysisLevel] = None
    timestamp: Optional[int] = None
    distribution: Optional[DistributionLevel] = None
    sharing_group_id: Optional[int] = None
    proposal_email_lock: Optional[bool] = None
    locked: Optional[bool] = None
    threat_level: Optional[ThreatLevel] = None
    publish_timestamp: Optional[int] = None
    sighting_timestamp: Optional[int] = None
    disable_correlation: Optional[bool] = None
    extends_uuid: Optional[UUID] = None
    protected: Optional[bool] = None
