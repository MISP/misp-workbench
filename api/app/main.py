import logging.config

from fastapi import FastAPI

from .routers import (
    attributes,
    auth,
    events,
    objects,
    organisations,
    roles,
    servers,
    users,
)

# setup loggers
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)

# Bootstrap application
app = FastAPI(title="misp-lite API", version="0.1.0")

# OAuth2 resource
app.include_router(auth.router, tags=["OAuth2"])

# Users resource
app.include_router(users.router, tags=["Users"])

# Organisations resource
app.include_router(organisations.router, tags=["Organisations"])

# Roles resource
app.include_router(roles.router, tags=["Roles"])

# Events resource
app.include_router(events.router, tags=["Events"])

# Attributes resource
app.include_router(attributes.router, tags=["Attributes"])

# Objects resource
app.include_router(objects.router, tags=["Objects"])

# Servers resource
app.include_router(servers.router, tags=["Servers"])
