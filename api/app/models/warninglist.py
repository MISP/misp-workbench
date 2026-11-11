from datetime import timedelta

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

# An organisation's list syncs from its source URL every sync_every_minutes:
# 0 for manual syncs only, or between these. The sweep runs every 5 minutes,
# which bounds its precision.
SYNC_EVERY_DEFAULT = 24 * 60
SYNC_EVERY_MIN = 15
SYNC_EVERY_MAX = 30 * 24 * 60
# A failing source is retried later and later (the interval doubling with each
# failure in a row), but never later than this, or than the interval itself.
SYNC_BACKOFF_CAP_MINUTES = 24 * 60


class Warninglist(Base):
    """A MISP warninglist: values known to be benign or too common to act on.

    Metadata only. Entries live in the ``misp-warninglist-entries``
    OpenSearch index (the big lists hold a million values each), except for
    ``substring`` and ``regex`` lists, which are few and small and are kept in
    ``patterns`` to be matched in memory.

    An organisation's own list (``org_id``, type ``local``) holds entries of
    several kinds (``WarninglistEntry``). Which indicators it matches is kept
    privately, apart from the MISP lists' hits: only the detection profiles
    that attach it leave those out. See app.repositories.local_warninglists.
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
    # How often it is synced, in minutes; 0: only when asked ("Sync now").
    sync_every_minutes = Column(
        Integer,
        nullable=False,
        default=SYNC_EVERY_DEFAULT,
        server_default=str(SYNC_EVERY_DEFAULT),
    )
    # Syncs in a row that failed, to back off from a failing source.
    sync_failures = Column(Integer, nullable=False, default=0, server_default="0")

    @property
    def sync_delay_minutes(self):
        """Minutes from the last sync to the next: the list's interval,
        doubled for each failure in a row (up to a day, or the interval if
        longer)."""
        every = self.sync_every_minutes
        if not every or not self.sync_failures:
            return every
        backed_off = every * 2 ** min(self.sync_failures, 16)
        return max(every, min(backed_off, SYNC_BACKOFF_CAP_MINUTES))

    @property
    def next_sync_at(self):
        """When the sweep syncs it next: None for a list synced by hand only
        (or not at all), or one never synced yet (the next sweep does)."""
        if not (self.source_url and self.enabled and self.sync_every_minutes):
            return None
        if self.synced_at is None:
            return None
        return self.synced_at + timedelta(minutes=self.sync_delay_minutes)


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
