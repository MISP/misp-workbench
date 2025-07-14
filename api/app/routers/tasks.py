from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.repositories import tasks as tasks_repository
from fastapi import APIRouter, Query, Security

router = APIRouter()


@router.get("/tasks/")
def get_tasks(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"])
):
    return tasks_repository.get_tasks()


@router.get("/tasks/workers")
def get_workers(
    user: user_schemas.User = Security(get_current_active_user, scopes=["tasks:read"])
):
    return tasks_repository.get_workers()


@router.post("/tasks/workers/{worker_id}/restart")
def restart_worker_by_id(
    worker_id: str,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["workers:update"]
    ),
):
    return tasks_repository.restart_worker(worker_id=worker_id)


@router.post("/tasks/workers/{worker_id}/grow")
def grow_worker_pool_by_id(
    worker_id: str,
    amount: int = Query(1),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["workers:update"]
    ),
):
    return tasks_repository.grow_worker_pool(worker_id=worker_id, amount=amount)


@router.post("/tasks/workers/{worker_id}/shrink")
def shrink_worker_pool_by_id(
    worker_id: str,
    amount: int = Query(1),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["workers:update"]
    ),
):
    return tasks_repository.shrink_worker_pool(worker_id=worker_id, amount=amount)


@router.post("/tasks/workers/{worker_id}/autoscale")
def shrink_worker_pool_by_id(
    worker_id: str,
    min: int = Query(1),
    max: int = Query(1),
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["workers:update"]
    ),
):
    return tasks_repository.autoscale_worker_pool(worker_id=worker_id, min=min, max=max)
