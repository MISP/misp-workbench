from app.models.attribute import Attribute  # noqa
from app.models.event import Event  # noqa
from app.models.object import Object  # noqa
from app.models.object_reference import ObjectReference  # noqa
from app.models.organisation import Organisation  # noqa
from app.models.role import Role  # noqa
from app.models.server import Server  # noqa
from app.models.sharing_groups import (  # noqa
    SharingGroup,
    SharingGroupOrganisation,
    SharingGroupServer,
)
from app.models.tag import AttributeTag, EventTag, Tag  # noqa
from app.models.user import User  # noqa

# fixes: sqlalchemy.exc.InvalidRequestError: When initializing mapper mapped class AAA->bbb, expression 'XXXX' failed to locate a name ('XXXX'). If this is a class name, consider adding this relationship() to the <class 'app.models.bbb.AAAA'> class after both dependent classes have been defined.
