from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

LabVisibility = Literal["personal", "global", "library"]
LabExecutionStatus = Literal["queued", "running", "success", "error", "interrupted"]


# ──────────────────────────────────────────────────────────────────────────
# Folders
# ──────────────────────────────────────────────────────────────────────────


class LabFolderBase(BaseModel):
    name: str
    visibility: LabVisibility
    parent_id: Optional[int] = None


class LabFolderCreate(LabFolderBase):
    pass


class LabFolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class LabFolder(LabFolderBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────
# Notebooks
# ──────────────────────────────────────────────────────────────────────────


class LabNotebookBase(BaseModel):
    name: str
    description: Optional[str] = None
    visibility: LabVisibility
    folder_id: Optional[int] = None


class LabNotebookCreate(LabNotebookBase):
    source: str = ""


class LabNotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    folder_id: Optional[int] = None
    source: Optional[str] = None


class LabNotebookSummary(LabNotebookBase):
    """Tree-view payload — omits source/cell_outputs to keep the tree fetch small."""

    id: int
    user_id: int
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class LabNotebook(LabNotebookBase):
    id: int
    user_id: int
    source: str = ""
    cell_outputs: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────
# Tree
# ──────────────────────────────────────────────────────────────────────────


class LabTree(BaseModel):
    """Single response that returns Personal + Global + Library trees so the
    left panel renders in one round trip. Library notebooks are read-only
    prebuilt content (seeded via CLI); users fork them to a personal copy
    before running."""

    folders: list[LabFolder]
    notebooks: list[LabNotebookSummary]


# ──────────────────────────────────────────────────────────────────────────
# Execution
# ──────────────────────────────────────────────────────────────────────────


class LabExecuteRequest(BaseModel):
    cell_id: str
    source: str
    timeout_seconds: int = 60


class LabExecution(BaseModel):
    id: int
    notebook_id: int
    user_id: int
    cell_id: str
    status: LabExecutionStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    outputs: list[dict[str, Any]] = Field(default_factory=list)
    execution_count: Optional[int] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LabQueryParams(BaseModel):
    filter: Optional[str] = None
