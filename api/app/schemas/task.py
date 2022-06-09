from pydantic import BaseModel
from uuid import UUID

class Task(BaseModel):
    task_id: UUID
    status: str
    message: str

    