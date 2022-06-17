from .attribute import Attribute  # noqa
from .event import Event  # noqa
from .object import Object  # noqa
from .object_reference import ObjectReference  # noqa
from .organisations import Organisation  # noqa
from .role import Role  # noqa
from .server import Server  # noqa
from .user import User  # noqa

# fixes: sqlalchemy.exc.InvalidRequestError: When initializing mapper mapped class AAA->bbb, expression 'XXXX' failed to locate a name ('XXXX'). If this is a class name, consider adding this relationship() to the <class 'app.models.bbb.AAAA'> class after both dependent classes have been defined.
