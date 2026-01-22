import uuid
from app.database import Base
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

class Taxonomy(Base):
    __tablename__ = "taxonomies"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    namespace = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    exclusive = Column(Boolean, nullable=False, default=False)
    required = Column(Boolean, nullable=False, default=False)
    highlighted = Column(Boolean, nullable=False, default=False)

    predicates = relationship("TaxonomyPredicate", lazy="subquery")


class TaxonomyPredicate(Base):
    __tablename__ = "taxonomy_predicates"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    taxonomy_id = Column(
        Integer, ForeignKey("taxonomies.id"), index=True, nullable=True
    )
    value = Column(String, nullable=False)
    expanded = Column(String, nullable=False)
    colour = Column(String, nullable=False)
    description = Column(String, nullable=False)
    exclusive = Column(Boolean, nullable=False, default=False)
    numerical_value = Column(Integer, index=True)

    entries = relationship("TaxonomyEntry", lazy="subquery")


class TaxonomyEntry(Base):
    __tablename__ = "taxonomy_entries"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    taxonomy_predicate_id = Column(
        Integer, ForeignKey("taxonomy_predicates.id"), index=True, nullable=True
    )
    value = Column(String, nullable=False)
    expanded = Column(String, nullable=False)
    colour = Column(String, nullable=False)
    description = Column(String, nullable=False)
    numerical_value = Column(Integer, index=True)
