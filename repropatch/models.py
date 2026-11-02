from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field

class Stage(StrEnum):
    QUEUED = "QUEUED"
    PREFLIGHT = "PREFLIGHT"
    REPRODUCING = "REPRODUCING"
    FROZEN = "FROZEN"
    PATCHING = "PATCHING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NOT_REPRODUCED = "NOT_REPRODUCED"
    BLOCKED = "BLOCKED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

TERMINAL = {Stage.VERIFIED, Stage.REJECTED, Stage.NOT_REPRODUCED, Stage.BLOCKED,
            Stage.BUDGET_EXCEEDED, Stage.ERROR, Stage.CANCELLED}

class RunCreate(BaseModel):
    case_id: str = Field(default="pagination-fixture", pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    method: Literal["W0", "W1"] = "W1"
    mode: Literal["fixture", "live"] = "fixture"
    title: str = Field(default="Active filter disappears on page 2", min_length=3, max_length=140)
    expected_behavior: str = Field(default="Keep the active filter on every page without breaking inactive filtering.", min_length=10, max_length=4000)
    video_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

class RunEvent(BaseModel):
    id: int
    run_id: str
    at: str
    stage: str
    kind: str
    message: str
    data: dict = Field(default_factory=dict)
