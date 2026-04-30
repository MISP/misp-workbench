from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class ReactorScript(Base):
    __tablename__ = "reactor_scripts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(32), nullable=False, default="python")
    source_uri = Column(String(512), nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    entrypoint = Column(String(255), nullable=False, default="handle")
    triggers = Column(JSONB, nullable=False, default=list, server_default="[]")
    status = Column(String(32), nullable=False, default="active")
    timeout_seconds = Column(Integer, nullable=False, default=60)
    max_writes = Column(Integer, nullable=False, default=100)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(32), nullable=True)
    last_run_id = Column(
        Integer,
        ForeignKey("reactor_runs.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class ReactorRun(Base):
    __tablename__ = "reactor_runs"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(
        Integer,
        ForeignKey("reactor_scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by = Column(JSONB, nullable=False, default=dict, server_default="{}")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="queued")
    error = Column(Text, nullable=True)
    log_uri = Column(String(512), nullable=True)
    writes_count = Column(Integer, nullable=False, default=0)
    celery_task_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
