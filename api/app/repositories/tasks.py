import os
from uuid import uuid4

from app.rediscli import get_redis
from app.schemas import task as task_schemas
from fastapi import HTTPException, status
from app.flower import FlowerClient
from redbeat import RedBeatSchedulerEntry
from celery.schedules import schedule as celery_schedule
from app.worker.tasks import celery_app

flower_url = os.environ.get("FLOWER_URL", "http://flower:5555/")


CELERY_WORKER_REDIS_DB = 0


def get_workers():

    response = FlowerClient.get(f"{flower_url}/workers?json=1")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workers from Flower API.",
        )

    data = response.json()

    for worker in data["data"]:
        hostname = worker["hostname"]
        FlowerClient.get(f"{flower_url}/worker/{hostname}")

    response = FlowerClient.get(f"{flower_url}/api/workers")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workers from Flower API.",
        )

    return response.json()


def get_tasks():
    response = FlowerClient.get(f"{flower_url}/api/tasks")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks from Flower API.",
        )

    return response.json()


def restart_worker(worker_id: str):
    response = FlowerClient.post(f"{flower_url}/apiworker/pool/restart/{worker_id}")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart worker {worker_id}. ",
        )

    return response.json()


def grow_worker_pool(worker_id: str, amount: int = 1):
    response = FlowerClient.post(
        f"{flower_url}/api/worker/pool/grow/{worker_id}",
        json={"amount": amount},
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grow worker pool for worker {worker_id}.",
        )

    return response.json()


def shrink_worker_pool(worker_id: str, amount: int = 1):
    response = FlowerClient.post(
        f"{flower_url}/api/worker/pool/shrink/{worker_id}",
        json={"amount": amount},
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to shrink worker pool for worker {worker_id}.",
        )

    return response.json()


def autoscale_worker_pool(worker_id: str, min: int = 1, max: int = 1):
    response = FlowerClient.post(
        f"{flower_url}/api/worker/pool/autoscale/{worker_id}",
        json={"min": min, "max": max},
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to autoscale worker pool for worker {worker_id}.",
        )

    return response.json()


def schedule_task(
    task_name: str,
    params: dict = None,
    schedule: task_schemas.ScheduleTaskSchedule = None,
):
    # TODO: Validate task_name, params and schedule

    scheduled_task_name = str(uuid4())
    interval = celery_schedule(int(schedule.every))
    entry = RedBeatSchedulerEntry(
        scheduled_task_name,
        task_name,
        interval,
        args=params.get("args", []) if params else [],
        kwargs=params.get("kwargs", {}) if params else {},
        app=celery_app,
        enabled=schedule.enabled if schedule else True,
    )
    entry.save()

    return {
        "task_name": task_name,
        "params": params,
        "schedule": schedule,
        "scheduled_task_name": scheduled_task_name,
        "status": "scheduled",
    }


def get_scheduled_tasks():
    RedisClient = get_redis(CELERY_WORKER_REDIS_DB)

    keys = RedisClient.keys("redbeat:*")

    scheduled_tasks = []
    for key in keys:
        if key in ["redbeat::lock", "redbeat::beat", "redbeat::schedule"]:
            continue

        task = RedBeatSchedulerEntry.from_key(key, app=celery_app)
        scheduled_tasks.append(scheduled_task_to_dict(task))

    return scheduled_tasks


def delete_scheduled_task(task_name: str):

    try:
        key = f"redbeat:{task_name}"
        task = RedBeatSchedulerEntry.from_key(key, app=celery_app)
        task.delete()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled task with name {task_name} not found.",
        )


def update_scheduled_task(
    task_name: str,
    params: dict = None,
    schedule: task_schemas.ScheduleTaskSchedule = None,
    enabled: bool = None,
):
    try:
        key = f"redbeat:{task_name}"
        task = RedBeatSchedulerEntry.from_key(key, app=celery_app)

        if params is not None:
            task.args = params.get("args", [])
            task.kwargs = params.get("kwargs", {})

        if schedule is not None:
            task.schedule = celery_schedule(int(schedule.every))
            task.enabled = schedule.enabled

        if enabled is not None:
            task.enabled = enabled

        task.save()

        return scheduled_task_to_dict(task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled task with name {task_name} not found.",
        )

def scheduled_task_to_dict(task):
    return {
            "id": task.name,
            "task_name": task.task,
            "args": task.args,
            "kwargs": task.kwargs,
            "schedule": str(task.schedule),
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "last_run_at": (
                task.last_run_at.isoformat() if task.last_run_at else None
            ),
            "total_run_count": task.total_run_count,
            "enabled": task.enabled,
            "status": "scheduled",
        }
    

