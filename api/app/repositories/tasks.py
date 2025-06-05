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
