from uuid import UUID

from pydantic import BaseModel


class Task(BaseModel):
    task_id: UUID
    status: str
    message: str

class ScheduleTaskSchedule(BaseModel):
    type: str = "interval"
    every: int
    unit: str = "seconds"
    at: str = None

class ScheduleTaskRequest(BaseModel):
    task_name: str
    params: list = []
    schedule: ScheduleTaskSchedule = None