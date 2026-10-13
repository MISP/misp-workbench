from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.indicator import Indicator

Action = Literal["approve", "reject", "snooze", "reopen"]
DecidedStatus = Literal["approved", "rejected", "snoozed"]


class ProfileRef(BaseModel):
    id: int
    name: str


class PendingIndicator(Indicator):
    # The profiles requiring approval that would select it once approved.
    pending_for: list[ProfileRef] = []


class ReviewQueuePage(BaseModel):
    total: int
    page: int
    size: int
    items: list[PendingIndicator]


class ReviewSummary(BaseModel):
    pending: int
    snoozed: int
    approved: int
    rejected: int
    # Profiles whose indicators go through the queue, and the ones approving
    # automatically.
    requiring_profiles: list[ProfileRef] = []
    auto_approve_profiles: list[ProfileRef] = []


class ReviewDecisionRequest(BaseModel):
    indicators: list[str] = Field(..., min_length=1, max_length=500)
    action: Action
    reason: Optional[str] = Field(None, max_length=2000)
    # Snooze for this many days.
    snooze_days: Optional[int] = Field(None, ge=1, le=365)
    # Rejecting: also add the value to the local allowlist warninglist.
    allowlist: bool = False

    @model_validator(mode="after")
    def _consistent(self):
        if self.action == "snooze" and not self.snooze_days:
            raise ValueError("snoozing needs snooze_days")
        if self.allowlist and self.action != "reject":
            raise ValueError("only a rejection can add an allowlist entry")
        return self


class ReviewDecisionResult(BaseModel):
    decided: int
    status: str


class ReviewDecision(BaseModel):
    indicator_uuid: str
    type: str
    value: str
    status: str
    reason: Optional[str] = None
    snoozed_until: Optional[datetime] = None
    allowlisted: bool = False
    # Only for audit admins and the decider's own organisation.
    user_email: Optional[str] = None
    user_organisation: Optional[str] = None
    decided_at: datetime


class ReviewDecisionPage(BaseModel):
    total: int
    page: int
    size: int
    items: list[ReviewDecision]


class ReviewHistoryEntry(BaseModel):
    # approved, rejected, snoozed, reopened
    action: str
    at: datetime
    # Only for audit admins and the decider's own organisation.
    user_email: Optional[str] = None
    user_organisation: Optional[str] = None
    reason: Optional[str] = None
    snoozed_until: Optional[str] = None
    allowlisted: bool = False


class IndicatorReviewDetail(BaseModel):
    decision: Optional[ReviewDecision] = None
    history: list[ReviewHistoryEntry] = []
