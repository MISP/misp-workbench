from app.database import Base
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    colour = Column(String, nullable=False)
    exportable = Column(Boolean, nullable=False, default=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hide_tag = Column(Boolean, nullable=False, default=False)
    numerical_value = Column(Integer)
    is_galaxy = Column(Boolean, nullable=False, default=False)
    is_custom_galaxy = Column(Boolean, nullable=False, default=False)
    local_only = Column(Boolean, nullable=False, default=False)

    def to_misp_format(self):
        """Convert the Tag to a MISP-compatible dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "colour": self.colour,
            "exportable": self.exportable,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "hide_tag": self.hide_tag,
            "numerical_value": self.numerical_value,
            "is_galaxy": self.is_galaxy,
            "is_custom_galaxy": self.is_custom_galaxy,
            "local_only": self.local_only,
        }


class EventTag(Base):
    __tablename__ = "event_tags"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    event = relationship("Event", lazy="subquery", overlaps="tags")
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    tag = relationship("Tag", lazy="subquery", overlaps="tags")
    local = Column(Boolean, nullable=False, default=False)


class AttributeTag(Base):
    __tablename__ = "attribute_tags"

    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer, ForeignKey("attributes.id"), nullable=False)
    attribute = relationship("Attribute", lazy="subquery", overlaps="tags")
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    tag = relationship("Tag", lazy="subquery", overlaps="tags")
    local = Column(Boolean, nullable=False, default=False)
