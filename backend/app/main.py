from fastapi import FastAPI
from .database import Base, engine
from .routers import users, events

# Bootstrap database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MISP API", description="MISP API", version="0.1.0")

# Users
app.include_router(users.router, tags=["Users"])

# Events
app.include_router(events.router, tags=["Events"])
