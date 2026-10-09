from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class Warninglist(Base):
    """A MISP warninglist: values known to be benign or too common to act on.

    Metadata only. Entries live in the ``misp-warninglist-entries``
    OpenSearch index (the big lists hold a million values each), except for
    ``substring`` and ``regex`` lists, which are few and small and are kept in
    ``patterns`` to be matched in memory.
    """

    __tablename__ = "warninglists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    type = Column(String(32), nullable=False)
    category = Column(String(64), nullable=True)
    version = Column(Integer, nullable=False)
    # Attribute types the list applies to; empty means every type.
    matching_attributes = Column(JSON, nullable=False, default=list)
    patterns = Column(JSON, nullable=True)
    entry_count = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_at = Column(DateTime(timezone=True), nullable=True)
