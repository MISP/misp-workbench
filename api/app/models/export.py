from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
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
    created_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
