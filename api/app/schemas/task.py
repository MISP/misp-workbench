from uuid import UUID

from pydantic import BaseModel


class Task(BaseModel):
    task_id: UUID
    status: str
    message: str
