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
    settings = relationship("UserSetting", lazy="subquery", cascade="all, delete-orphan")

    def can_create_pulled_event(self, event: MISPEvent) -> bool:
        """
        see: app/Model/Event.php::_add()
        """

        if (
            event.orgc_id is not None
            and event.orgc_id == self.org_id
            and (self.role.perm_sync or self.role.perm_admin)
        ):
            return True

        if event.orgc.uuid == self.organisation.uuid and (
            self.roleperm_sync or self.role.perm_admin
        ):
            return True

        return False

    def can_publish_event(self) -> bool:
        if self.role.perm_publish:
            return True

        return False
