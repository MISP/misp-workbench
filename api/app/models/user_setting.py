from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from app.database import Base


class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    namespace = Column(String, unique=True, index=True)
    value = Column(JSON)