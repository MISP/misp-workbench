from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Task(BaseModel):
    task_id: UUID
    status: str
    message: str

class ScheduleTaskSchedule(BaseModel):
    type: str = "interval"
    # interval fields
    every: Optional[int] = None
    # crontab fields
    minute: str = "*"
    hour: str = "*"
    day_of_week: str = "*"
    day_of_month: str = "*"
    month_of_year: str = "*"

class ScheduleTaskRequest(BaseModel):
    task_name: str
    params: dict = {}
    schedule: ScheduleTaskSchedule = None
    enabled: bool = False

class UpdateScheduledTaskRequest(BaseModel):
    params: dict = None
    schedule: ScheduleTaskSchedule = None
    enabled: bool = None