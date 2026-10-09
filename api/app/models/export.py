from sqlalchemy import (
    JSON,
    BigInteger,
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


class Export(Base):
    """An async IOC export job.

    A user supplies an OpenSearch query against the attributes or events
    index plus a target format; a Celery task runs the query, transforms the
    results, and stores the artifact in local/Garage storage. The row tracks
    job state and a pointer (``storage_key``) to the produced file.
    """

    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    index_target = Column(String(50), nullable=False, default="attributes")
    format = Column(String(20), nullable=False, default="json")
    # Event distribution level for MISP-format exports (0–4); null otherwise.
    distribution = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="queued")
    storage_key = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    record_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    celery_task_id = Column(String(128), nullable=True)
    # Recurring exports: when ``schedule`` is set the job is registered with the
    # redbeat scheduler and re-runs in place (overwriting its own artifact).
    schedule = Column(JSON, nullable=True)
    scheduled_task_name = Column(String(128), nullable=True)
    schedule_enabled = Column(Boolean, nullable=False, default=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    # sha256 of the stored artifact, served as its ETag: a re-run that produces
    # the same bytes keeps answering conditional requests with a 304.
    checksum = Column(String(64), nullable=True)
    # Incremental feeds: every run also writes a delta of what changed since the
    # previous run. ``cursor`` is the unix time the latest run read the index
    # at; the full artifact is current as of it.
    incremental = Column(Boolean, nullable=False, default=False, server_default="false")
    cursor = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class ExportDelta(Base):
    """What changed between two runs of an incremental export.

    Covers attributes written at or after ``since`` and up to ``until`` (the
    run's cursor), soft-deleted ones included as tombstones. Consecutive deltas
    chain: each one's ``since`` is the previous one's ``until``.
    """

    __tablename__ = "export_deltas"
    __table_args__ = (UniqueConstraint("export_id", "seq"),)

    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(
        Integer, ForeignKey("exports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq = Column(Integer, nullable=False)
    since = Column(BigInteger, nullable=False)
    until = Column(BigInteger, nullable=False)
    storage_key = Column(String(512), nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    file_size = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False)
