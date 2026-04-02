from app.auth.utils import role_has_scope
from app.database import Base
from pymisp import MISPEvent
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), index=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)

    role = relationship("Role")
    organisation = relationship(
        "Organisation", backref=backref("users", cascade="all, delete-orphan")
    )
    settings = relationship("UserSetting", back_populates="user")

    def can_create_pulled_event(self, event: MISPEvent) -> bool:
        """
        see: app/Model/Event.php::_add()
        """
        has_sync = role_has_scope(self.role.scopes, "servers:pull")
        has_admin = role_has_scope(self.role.scopes, "users:*")

        if (
            event.orgc_id is not None
            and event.orgc_id == self.org_id
            and (has_sync or has_admin)
        ):
            return True

        if event.orgc.uuid == self.organisation.uuid and (has_sync or has_admin):
            return True

        return False

    def can_publish_event(self) -> bool:
        return role_has_scope(self.role.scopes, "events:publish")


from app.models.user_setting import UserSetting
