import logging.config

from app.routers import (
    api_keys,
    attachments,
    attributes,
    auth,
    diagnostics,
    events,
    feeds,
    galaxies,
    hunts,
    mcp,
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
    notifications,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

# setup loggers
# Import and use our custom logging setup
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from setup_logging import setup_logging

setup_logging()

# MCP server (mounted as ASGI sub-app)
mcp_app = mcp.mcp.http_app(path="/")

# Bootstrap application
app = FastAPI(title="misp-workbench API", version="0.1.0", lifespan=mcp_app.lifespan)

# Add CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:6274",
]
extra_origins = os.environ.get("CORS_ORIGINS", "")
if extra_origins:
    origins += [o.strip() for o in extra_origins.split(",") if o.strip()]
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

# Hunts resource
app.include_router(hunts.router, tags=["Hunts"])

# Notifications resource
app.include_router(notifications.router, tags=["Notifications"])

# API Keys resource
app.include_router(api_keys.router, tags=["API Keys"])

# MCP config endpoint (must be registered before the /mcp mount)
app.include_router(mcp.router, tags=["MCP"])

# MCP server (Streamable HTTP at /mcp)
app.mount("/mcp", mcp_app)

add_pagination(app)
