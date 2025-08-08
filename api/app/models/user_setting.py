from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from app.database import Base
from sqlalchemy.orm import relationship

class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    namespace = Column(String, unique=True, index=True)
    value = Column(JSON)
    user = relationship("User", back_populates="settings")