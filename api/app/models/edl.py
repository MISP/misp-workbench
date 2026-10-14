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


class Edl(Base):
    """An external dynamic list: one detection profile's values of one kind
    (IPs, domains, URLs or hashes), in the format a firewall vendor expects.

    It is rebuilt every ``refresh_minutes`` into storage and served from
    there, at a URL carrying one of its tokens (``EdlToken``).
    """

    __tablename__ = "edls"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Deleting a profile an EDL reads is refused (see detection_profiles.users_of).
    profile_id = Column(
        Integer,
        ForeignKey("detection_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    list_type = Column(String(20), nullable=False)
    vendor = Column(String(20), nullable=False)
    # At most this many entries, the highest scored; null: the vendor's.
    max_entries = Column(Integer, nullable=True)
    include_subdomains = Column(Boolean, nullable=False, default=False)
    refresh_minutes = Column(Integer, nullable=False, default=15)
    enabled = Column(Boolean, nullable=False, default=True)

    storage_key = Column(String(512), nullable=True)
    # sha256 of the list, its ETag.
    checksum = Column(String(64), nullable=True)
    entry_count = Column(Integer, nullable=True)
    # Entries left out by max_entries, the lowest scored.
    truncated = Column(Integer, nullable=True)
    built_at = Column(DateTime(timezone=True), nullable=True)
    build_error = Column(Text, nullable=True)

    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class EdlToken(Base):
    """A read-only credential for one EDL, carried in its URL (firewalls
    can't send an Authorization header). Only its sha256 is kept."""

    __tablename__ = "edl_tokens"

    id = Column(Integer, primary_key=True, index=True)
    edl_id = Column(
        Integer, ForeignKey("edls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    # The token's first characters, to tell tokens apart.
    prefix = Column(String(16), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    # Addresses or networks it may be used from; empty: anywhere.
    allowed_ips = Column(JSON, nullable=False, default=list)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(64), nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
