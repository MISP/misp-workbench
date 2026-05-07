from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB


class LabFolder(Base):
    __tablename__ = "lab_folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_id = Column(
        Integer,
        ForeignKey("lab_folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(255), nullable=False)
    visibility = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class LabNotebook(Base):
    __tablename__ = "lab_notebooks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    folder_id = Column(
        Integer,
        ForeignKey("lab_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    visibility = Column(String(16), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(Text, nullable=False, default="", server_default="")
    cell_outputs = Column(JSONB, nullable=False, default=dict, server_default="{}")
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class LabExecution(Base):
    __tablename__ = "lab_executions"

    id = Column(Integer, primary_key=True, index=True)
    notebook_id = Column(
        Integer,
        ForeignKey("lab_notebooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cell_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    outputs = Column(JSONB, nullable=False, default=list, server_default="[]")
    execution_count = Column(Integer, nullable=True)
    celery_task_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
