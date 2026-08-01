"""Tests for API request/response schema validation."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vibeguard.api.schemas import RepositoryResponse, RepositorySubmitRequest
from vibeguard.core.repository_status import RepositoryStatus


def test_repository_submit_request_requires_repo_url():
    with pytest.raises(ValidationError):
        RepositorySubmitRequest.model_validate({})


def test_repository_submit_request_accepts_repo_url():
    request = RepositorySubmitRequest.model_validate({"repo_url": "https://github.com/o/r"})
    assert request.repo_url == "https://github.com/o/r"


def test_repository_response_builds_from_orm_like_object():
    class _FakeRow:
        id = 1
        source_url = "https://github.com/o/r"
        owner = "o"
        name = "r"
        status = RepositoryStatus.PENDING
        rejection_reason = None
        files_truncated = False
        truncation_reason = None
        total_files_stored = 0
        total_files_skipped = 0
        total_bytes_stored = 0
        scan_incomplete = False
        scan_incomplete_reason = None
        scan_failure_reason = None
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

    response = RepositoryResponse.model_validate(_FakeRow())
    assert response.owner == "o"
    assert response.status == RepositoryStatus.PENDING
