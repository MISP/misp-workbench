import logging.config

from app.routers import (
    attachments,
    attributes,
    auth,
    diagnostics,
    events,
    feeds,
    galaxies,
    modules,
    object_templates,
    objects,
    organisations,
    roles,
    servers,
    sharing_groups,
    tags,
    taxonomies,
    users,
    reports,
    tasks,
    correlations,
    sightings,
    runtime_settings,
    user_settings,
    notifications
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

# setup loggers
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)

# Bootstrap application
app = FastAPI(title="misp-workbench API", version="0.1.0")

# Add CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Object Templates resource
app.include_router(object_templates.router, tags=["Object Templates"])

# Servers resource
app.include_router(servers.router, tags=["Servers"])

# Sharing Groups resource
app.include_router(sharing_groups.router, tags=["Sharing Groups"])

# Tags resource
app.include_router(tags.router, tags=["Tags"])

# Taxonomies resource
app.include_router(taxonomies.router, tags=["Taxonomies"])

# Modules resource
app.include_router(modules.router, tags=["Modules"])

# Feeds resource
app.include_router(feeds.router, tags=["Feeds"])

# Galaxies resource
app.include_router(galaxies.router, tags=["Galaxies"])

# Attachments resource
app.include_router(attachments.router, tags=["Attachments"])

# Reports resource
app.include_router(reports.router, tags=["Event Reports"])

# Tasks resource
app.include_router(tasks.router, tags=["Tasks"])

# Correlations resource
app.include_router(correlations.router, tags=["Correlations"])

# Sightings resource
app.include_router(sightings.router, tags=["Sightings"])

# Runtime Settings resource
app.include_router(runtime_settings.router, tags=["Runtime Settings"])

# User Settings resource
app.include_router(user_settings.router, tags=["User Settings"])

# Diagnostics resource
app.include_router(diagnostics.router, tags=["Diagnostics"])

# Notifications resource
app.include_router(notifications.router, tags=["Notifications"])

add_pagination(app)
