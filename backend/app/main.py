from fastapi import FastAPI
from .models.database import Base, engine
from .routers import users, events, attributes

# Bootstrap application
app = FastAPI(title="MISP3 API", version="0.1.0")

# Users resource
app.include_router(users.router, tags=["Users"])

# Events resource
app.include_router(events.router, tags=["Events"])

# Attributes resource
app.include_router(attributes.router, tags=["Attributes"])
