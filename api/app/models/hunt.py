from app.database import Base
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text


class Hunt(Base):
    __tablename__ = "hunts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    query = Column(Text, nullable=False)
    index_target = Column(String(50), nullable=False, default="attributes")
    status = Column(String(50), nullable=False, default="active")
    last_run_at = Column(DateTime, nullable=True)
    last_match_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class HuntRunHistory(Base):
    __tablename__ = "hunt_run_history"

    id = Column(Integer, primary_key=True, index=True)
    hunt_id = Column(Integer, ForeignKey("hunts.id", ondelete="CASCADE"), nullable=False, index=True)
    run_at = Column(DateTime(timezone=True), nullable=False)
    match_count = Column(Integer, nullable=False)
