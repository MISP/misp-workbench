import os
from uuid import uuid4

from app.schemas import task as task_schemas
from fastapi import HTTPException, status
from app.flower import FlowerClient
from redbeat import RedBeatSchedulerEntry
from celery.schedules import schedule as celery_schedule
from app.worker.tasks import celery_app

flower_url = os.environ.get("FLOWER_URL", "http://flower:5555/")


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
        args=[params, scheduled_task_name],
        app=celery_app,
    )
    entry.save()

    return {
        "task_name": task_name,
        "params": params,
        "schedule": schedule,
        "scheduled_task_name": scheduled_task_name,
        "status": "scheduled",
    }
