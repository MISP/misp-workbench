import uuid

import logging
from app.database import Base
from app.models.event import DistributionLevel
from app.services.attachments import  get_b64_attachment
from sqlalchemy import BigInteger, Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.settings import Settings, get_settings


logger = logging.getLogger(__name__)


class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    object_id = Column(Integer, ForeignKey("objects.id"))
    object_relation = Column(String(255), index=True)
    category = Column(String(255), index=True)
    type = Column(String(100), index=True)
    value = Column(String())
    to_ids = Column(Boolean, default=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    timestamp = Column(Integer, nullable=False, default=0)
    distribution: Mapped[DistributionLevel] = mapped_column(
        Enum(DistributionLevel, name="distribution_level"),
        nullable=False,
        default=DistributionLevel.INHERIT_EVENT,
    )
    sharing_group_id = Column(
        Integer, ForeignKey("sharing_groups.id"), index=True, nullable=True
    )
    comment = Column(String())
    deleted = Column(Boolean, default=False)
    disable_correlation = Column(Boolean, default=False)
    first_seen = Column(BigInteger(), index=True)
    last_seen = Column(BigInteger(), index=True)
    event = relationship(
        "Event",
        lazy="joined",
        viewonly=True
    )
    tags = relationship("Tag", secondary="attribute_tags", lazy="subquery")

    def to_misp_format(
        self,
        settings: Settings = get_settings(),
    ):
        """Convert the Attribute to a MISP-compatible dictionary representation."""

        attr_json = {
            "id": self.id,
            "event_id": self.event_id,
            "object_id": self.object_id,
            "object_relation": self.object_relation,
            "category": self.category,
            "type": self.type,
            "value": self.value,
            "to_ids": self.to_ids,
            "uuid": str(self.uuid),
            "timestamp": self.timestamp,
            "distribution": self.distribution.value if self.distribution else DistributionLevel.INHERIT_EVENT,
            "sharing_group_id": self.sharing_group_id if self.sharing_group_id else None,
            "comment": self.comment,
            "deleted": self.deleted,
            "disable_correlation": self.disable_correlation,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "Tag": [tag.to_misp_format() for tag in self.tags],
        }

        # if its a file attribute, we need to handle it differently
        if self.type in ["malware-sample", "attachment"]:
            try:
                attr_json["data"] = get_b64_attachment(self.uuid, settings)
            except Exception as e:
                logger.error(f"Error storing attachment: {str(e)}")
                print(f"Error fetching file from storage: {str(e)}")

        return attr_json
