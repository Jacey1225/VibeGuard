"""Response bodies for the vulnerability findings endpoint."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from vibeguard.core.finding import FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


class FindingResponse(BaseModel):
    """One persisted vulnerability finding."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: VulnCategory
    severity: Severity
    source: FindingSource
    title: str
    description: str
    remediation: str
    relative_path: str
    line_number: int | None
    model: str | None
    created_at: datetime


class FindingListResponse(BaseModel):
    """Every finding for one repository, worst-first."""

    findings: list[FindingResponse]
