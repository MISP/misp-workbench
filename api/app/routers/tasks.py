import uuid
from app.auth.security import get_current_active_user
from app.schemas import user as user_schemas
from app.schemas import task as task_schemas
from app.repositories import tasks as tasks_repository
from fastapi import APIRouter, Query, Security
from fastapi import HTTPException

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


@router.post("/tasks/schedule")
def schedule_task(
    task: task_schemas.ScheduleTaskRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["scheduled_tasks:create"]
    ),
):

    return tasks_repository.schedule_task(
        task_name=task.task_name, params=task.params, schedule=task.schedule, enabled=task.enabled
    )


@router.get("/tasks/scheduled")
def get_scheduled_tasks(
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["scheduled_tasks:read"]
    ),
):

    return tasks_repository.get_scheduled_tasks()


@router.delete("/tasks/scheduled/{task_name}")
def delete_scheduled_task(
    task_name: str,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["scheduled_tasks:delete"]
    ),
):
    try:
        uuid.UUID(task_name, version=4)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid task_name, must be a valid UUID4 string"
        )

    tasks_repository.delete_scheduled_task(task_name=task_name)


@router.patch("/tasks/scheduled/{task_name}")
def update_scheduled_task(
    task_name: str,
    task: task_schemas.UpdateScheduledTaskRequest,
    user: user_schemas.User = Security(
        get_current_active_user, scopes=["scheduled_tasks:update"]
    ),
):

    try:
        uuid.UUID(task_name, version=4)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid task_name, must be a valid UUID4 string"
        )

    return tasks_repository.update_scheduled_task(task_name=task_name, params=task.params, schedule=task.schedule, enabled=task.enabled)
