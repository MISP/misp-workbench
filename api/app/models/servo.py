from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Servo(Base):
    """A user-authored OpenSearch ingest pipeline (Tech Lab transformation servo).

    Postgres is the source of truth: ``processors`` is compiled into an
    ``_ingest/pipeline`` named ``servo_<slug>`` and referenced from the
    API-owned chain pipeline. See ``app.services.tech_lab.servos.chain``.
    """

    __tablename__ = "servos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    processors = Column(JSONB, nullable=False, default=list, server_default="[]")
    target_index = Column(String(255), nullable=False, default="misp-attributes")
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def drops_documents(self) -> bool:
        """Whether this servo can discard attributes at ingestion.

        Derived from the processors rather than stored, so it can never drift
        out of step with them. The import is deferred because the chain service
        imports this module.
        """
        from app.services.tech_lab.servos.chain import drops_documents

        return drops_documents(self.processors)


class ServoRun(Base):
    """One backfill: re-running the ingest chain over existing attributes.

    A backfill is `_update_by_query` against `misp-attributes`. OpenSearch runs
    it asynchronously and hands back a task id, so the row carries that id and
    is filled in as the task is polled. It records what was asked for
    (`filter_query`) as well as what happened, because a backfill rewrites live
    documents and "which ones did we touch, and when" is the question asked
    afterwards.
    """

    __tablename__ = "servo_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Lucene filter the operator scoped the run to; empty means every attribute.
    filter_query = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    # OpenSearch's own task id, e.g. "bqDK0KuGSnGylyPBiuetgg:14721".
    opensearch_task_id = Column(String(128), nullable=True)
    celery_task_id = Column(String(128), nullable=True)
    total = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
