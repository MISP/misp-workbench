import os

from fastapi import HTTPException, Query, status
from app.flower import FlowerClient

flower_url = os.environ.get("FLOWER_API_URL", "http://flower:5555/api")


def get_workers():
    response = FlowerClient.get(f"{flower_url}/workers")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workers from Flower API.",
        )

    return response.json()


def get_tasks():
    response = FlowerClient.get(f"{flower_url}/tasks")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks from Flower API.",
        )

    return response.json()


def restart_worker(worker_id: str):
    response = FlowerClient.post(f"{flower_url}/worker/pool/restart/{worker_id}")
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart worker {worker_id}. ",
        )

    return response.json()


def grow_worker_pool(worker_id: str, amount: int = 1):
    response = FlowerClient.post(
        f"{flower_url}/worker/pool/grow/{worker_id}",
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
        f"{flower_url}/worker/pool/shrink/{worker_id}",
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
        f"{flower_url}/worker/pool/autoscale/{worker_id}",
        json={"min": min, "max": max},
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to autoscale worker pool for worker {worker_id}.",
        )

    return response.json()
