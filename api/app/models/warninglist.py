from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


class Warninglist(Base):
    """A MISP warninglist: values known to be benign or too common to act on.

    Metadata only. Entries live in the ``misp-warninglist-entries``
    OpenSearch index (the big lists hold a million values each), except for
    ``substring`` and ``regex`` lists, which are few and small and are kept in
    ``patterns`` to be matched in memory.

    An organisation's own list (``org_id``, type ``local``) holds entries of
    several kinds (``WarninglistEntry``) and flags what it matches apart from
    the MISP lists (``local_list_hits``): only the detection profiles that
    attach it leave those out. See app.repositories.local_warninglists.
    """

    __tablename__ = "warninglists"

    id = Column(Integer, primary_key=True, index=True)
    # Unique among the MISP lists, and within an organisation (see the
    # a0b1c2d3e4f5 migration's partial indexes).
    name = Column(String(255), nullable=False)
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
    org_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # A plain list (one entry per line) the entries are synced from.
    source_url = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_error = Column(Text, nullable=True)


class WarninglistEntry(Base):
    """One entry of an organisation's list.

    ``kind``: ``value`` (exact), ``cidr`` (an address range), ``suffix`` (a
    domain and its subdomains) or ``regex``. Expired entries no longer match.
    """

    __tablename__ = "warninglist_entries"
    __table_args__ = (UniqueConstraint("warninglist_id", "kind", "value"),)

    id = Column(Integer, primary_key=True)
    warninglist_id = Column(
        Integer,
        ForeignKey("warninglists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(String(16), nullable=False)
    value = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # manual, import or sync (from source_url)
    origin = Column(String(16), nullable=False, default="manual")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
