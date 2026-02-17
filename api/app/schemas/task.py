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
    enabled: bool = True

class ScheduleTaskRequest(BaseModel):
    task_name: str
    params: dict = {}
    schedule: ScheduleTaskSchedule = None

class UpdateScheduledTaskRequest(BaseModel):
    params: dict = None
    schedule: ScheduleTaskSchedule = None
    enabled: bool = None