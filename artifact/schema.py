from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum
from datetime import datetime
import uuid

class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    WAIT = "wait"
    ASSERT = "assert"
    EXTRACT = "extract"
    SCREENSHOT = "screenshot"

class LocatorStrategy(str, Enum):
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    NAME = "name"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    ARIA = "aria"

class Locator(BaseModel):
    strategy: LocatorStrategy
    value: str
    fallbacks: list = Field(default_factory=list)
    description: str = ""

class ActionStep(BaseModel):
    step_id: int
    action: ActionType
    description: str
    locator: Optional[Locator] = None
    value: Optional[str] = None
    param_ref: Optional[str] = None
    extract_as: Optional[str] = None
    checkpoint: Optional[str] = None
    timeout_ms: int = 5000
    on_error: str = "fail"

class InputParam(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    example: Any = None

class OutputField(BaseModel):
    name: str
    type: str
    description: str
    extract_from: str

class CapabilityStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"

class Capability(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    version: str = "1.0.0"
    status: CapabilityStatus = CapabilityStatus.DRAFT
    target_url: str
    tenant_id: str = "default"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    inputs: list = Field(default_factory=list)
    outputs: list = Field(default_factory=list)
    steps: list = Field(default_factory=list)
    success_condition: str = ""
    tags: list = Field(default_factory=list)
    allowlist: list = Field(default_factory=list)
