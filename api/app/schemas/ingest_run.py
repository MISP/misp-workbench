from typing import Literal, Optional

from pydantic import BaseModel


class IngestRun(BaseModel):
    """A feed fetch or server pull, see ``app.services.ingest_runs``."""

    status: Literal["queued", "running", "cancelling", "done", "failed", "cancelled"]
    user_id: Optional[int] = None
    queued_at: Optional[int] = None
    started_at: Optional[int] = None
    updated_at: Optional[int] = None
    finished_at: Optional[int] = None
    # Events listed for the run, ingested, failed, and still waiting (only
    # while it runs). Single-task feeds (CSV, freetext, JSON) list none.
    total: int = 0
    done: int = 0
    failed: int = 0
    pending: Optional[int] = None
    error: Optional[str] = None


class IngestRunStatus(BaseModel):
    current: Optional[IngestRun] = None
    last: Optional[IngestRun] = None
