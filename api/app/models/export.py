from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

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
    status = Column(String(50), nullable=False, default="queued")
    storage_key = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)
    record_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    celery_task_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
