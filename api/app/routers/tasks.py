from app.auth.auth import get_current_active_user
from app.schemas import user as user_schemas
from app.repositories import tasks as tasks_repository
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status

router = APIRouter()

@router.get("/tasks/")
def get_tasks(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["tasks:read"]
    )
):
    return tasks_repository.get_tasks()

@router.get("/tasks/workers")
def get_workers(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["tasks:read"]
    )
):
    return tasks_repository.get_workers()

