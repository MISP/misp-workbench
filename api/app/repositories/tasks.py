import os
import time
from uuid import uuid4

from app.rediscli import get_redis
from app.schemas import task as task_schemas
from fastapi import HTTPException, status
from app.flower import FlowerClient
from redbeat import RedBeatSchedulerEntry
from celery.schedules import crontab, schedule as celery_schedule
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


def get_tasks(limit: int = 100, offset: int = 0):
    response = FlowerClient.get(
        f"{flower_url}/api/tasks",
        params={"limit": limit, "offset": offset},
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks from Flower API.",
        )

    items = response.json()
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "has_more": len(items) == limit,
    }


def get_active_tasks():
    inspector = celery_app.control.inspect(timeout=2)
    active = inspector.active() or {}
    reserved = inspector.reserved() or {}

    # Celery reports `time_start` on the monotonic clock. On Linux hosts (and
    # containers sharing a kernel) CLOCK_MONOTONIC is system-wide, so we can
    # convert to a wall-clock timestamp by anchoring both clocks here.
    monotonic_to_epoch = time.time() - time.monotonic()

    tasks = {}

    for worker, worker_tasks in active.items():
        for task in worker_tasks or []:
            uuid = task.get("id")
            if not uuid:
                continue
            started_monotonic = task.get("time_start")
            started = (
                started_monotonic + monotonic_to_epoch
                if started_monotonic is not None
                else None
            )
            tasks[uuid] = {
                "uuid": uuid,
                "name": task.get("name"),
                "worker": worker,
                "args": task.get("args"),
                "kwargs": task.get("kwargs"),
                "received": started,
                "started": started,
                "state": "STARTED",
            }

    for worker, worker_tasks in reserved.items():
        for task in worker_tasks or []:
            uuid = task.get("id")
            if not uuid or uuid in tasks:
                continue
            tasks[uuid] = {
                "uuid": uuid,
                "name": task.get("name"),
                "worker": worker,
                "args": task.get("args"),
                "kwargs": task.get("kwargs"),
                "received": None,
                "started": None,
                "state": "RESERVED",
            }

    return tasks


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
    enabled: bool = False,
    user_id: str = None
):
    # TODO: Validate task_name, params and schedule

    scheduled_task_name = str(uuid4())
    if schedule and schedule.type == "crontab":
        interval = crontab(
            minute=schedule.minute,
            hour=schedule.hour,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
            month_of_year=schedule.month_of_year,
        )
    else:
        interval = celery_schedule(int(schedule.every))

    kwargs = params.get("kwargs", {}) if params else {}
    if "user_id" not in kwargs:
        kwargs["user_id"] = user_id

    entry = RedBeatSchedulerEntry(
        scheduled_task_name,
        task_name,
        interval,
        args=params.get("args", []) if params else [],
        kwargs=params.get("kwargs", {}) if params else {},
        app=celery_app,
        enabled=enabled
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
    user_id: str = None
):
    try:
        key = f"redbeat:{task_name}"
        task = RedBeatSchedulerEntry.from_key(key, app=celery_app)

        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheduled task with name {task_name} not found.",
            )
        
        if params is not None:
            task.args = params.get("args", [])
            task.kwargs = params.get("kwargs", {})
            
        if not "user_id" in task.kwargs:
            task.kwargs["user_id"] = user_id

        if schedule is not None:
            if schedule.type == "crontab":
                task.schedule = crontab(
                    minute=schedule.minute,
                    hour=schedule.hour,
                    day_of_week=schedule.day_of_week,
                    day_of_month=schedule.day_of_month,
                    month_of_year=schedule.month_of_year,
                )
            else:
                task.schedule = celery_schedule(int(schedule.every))

        if enabled is not None:
            task.enabled = enabled

        task.save()

        return scheduled_task_to_dict(task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled task with name {task_name} not found.",
        )


def delete_scheduled_tasks_for_feed(feed_id: int):
    """Delete all RedBeat scheduled tasks whose kwargs contain the given feed_id."""
    RedisClient = get_redis(CELERY_WORKER_REDIS_DB)
    keys = RedisClient.keys("redbeat:*")

    for key in keys:
        if key in ["redbeat::lock", "redbeat::beat", "redbeat::schedule"]:
            continue
        try:
            task = RedBeatSchedulerEntry.from_key(key, app=celery_app)
            if task.kwargs.get("feed_id") == feed_id:
                task.delete()
        except Exception:
            continue


def delete_scheduled_tasks_for_hunt(hunt_id: int):
    """Delete all RedBeat scheduled tasks whose kwargs contain the given hunt_id."""
    RedisClient = get_redis(CELERY_WORKER_REDIS_DB)
    keys = RedisClient.keys("redbeat:*")

    for key in keys:
        if key in ["redbeat::lock", "redbeat::beat", "redbeat::schedule"]:
            continue
        try:
            task = RedBeatSchedulerEntry.from_key(key, app=celery_app)
            if task.kwargs.get("hunt_id") == hunt_id:
                task.delete()
        except Exception:
            continue


def scheduled_task_to_dict(task):
    return {
        "id": task.name,
        "task_name": task.task,
        "args": task.args,
        "kwargs": task.kwargs,
        "schedule": str(task.schedule),
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "last_run_at": (task.last_run_at.isoformat() if task.last_run_at else None),
        "total_run_count": task.total_run_count,
        "enabled": task.enabled,
        "status": "scheduled",
    }
