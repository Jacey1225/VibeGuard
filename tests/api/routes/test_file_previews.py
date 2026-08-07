"""Tests for GET /repositories/{id}/files/preview through the full request/response cycle.

This endpoint replaces RealFindingCard.tsx's old unauthenticated,
per-card, direct-to-GitHub browser fetch (Bug A in
.claude/pipeline/20260807-decide-remediation-fetch-bug/intake-spec.md).
These tests cover the specific failure modes the spec calls out as
needing a clear, distinct message instead of a bare "failed to fetch":
repo not found, file not found, binary/oversized file skipped at
intake, and a requested line outside the file's current stored length.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.api.dependencies import get_db_session
from vibeguard.api.error_handlers import (
    handle_file_not_found_in_repository,
    handle_file_not_previewable,
    handle_line_out_of_range,
    handle_repository_not_found,
)
from vibeguard.api.routes.file_previews import router
from vibeguard.core.file_preview import LineOutOfRangeError
from vibeguard.engine.file_preview import FileNotFoundInRepositoryError, FileNotPreviewableError
from vibeguard.engine.vuln_scan import RepositoryNotFoundError


def _build_test_app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RepositoryNotFoundError, handle_repository_not_found)
    app.add_exception_handler(FileNotFoundInRepositoryError, handle_file_not_found_in_repository)
    app.add_exception_handler(FileNotPreviewableError, handle_file_not_previewable)
    app.add_exception_handler(LineOutOfRangeError, handle_line_out_of_range)
    app.dependency_overrides[get_db_session] = lambda: db_session
    return app


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="octocat", name="Hello-World")
    session.add(repository)
    session.flush()
    return repository


def test_preview_file_happy_path_returns_windowed_content(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="src/app.py",
            size_bytes=100,
            content="\n".join(f"line{i}" for i in range(1, 21)),
        )
    )
    db_session.commit()
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        f"/repositories/{repository.id}/files/preview",
        params={"path": "src/app.py", "line": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["relative_path"] == "src/app.py"
    assert body["highlight_line"] == 10
    assert [line["number"] for line in body["lines"]] == list(range(5, 16))
    assert body["lines"][5]["text"] == "line10"


def test_preview_file_unknown_repository_returns_404_with_specific_detail(db_session: Session):
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        "/repositories/999/files/preview", params={"path": "src/app.py", "line": 1}
    )

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


def test_preview_file_unknown_path_returns_404_with_specific_detail(db_session: Session):
    repository = _make_repository(db_session)
    db_session.commit()
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        f"/repositories/{repository.id}/files/preview",
        params={"path": "does/not/exist.py", "line": 1},
    )

    assert response.status_code == 404
    assert "does/not/exist.py" in response.json()["detail"]


def test_preview_file_binary_or_oversized_skipped_file_returns_422_not_bare_network_error(
    db_session: Session,
):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="assets/logo.png",
            size_bytes=999_999,
            is_skipped=True,
            skip_reason="binary",
        )
    )
    db_session.commit()
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        f"/repositories/{repository.id}/files/preview",
        params={"path": "assets/logo.png", "line": 1},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "logo.png" in detail
    assert detail != "failed to fetch"


def test_preview_file_line_out_of_range_returns_422_with_specific_detail(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="src/app.py",
            size_bytes=10,
            content="one\ntwo\nthree",
        )
    )
    db_session.commit()
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        f"/repositories/{repository.id}/files/preview",
        params={"path": "src/app.py", "line": 100},
    )

    assert response.status_code == 422
    assert "100" in response.json()["detail"]


def test_preview_file_rejects_non_positive_line_with_422_validation_error(db_session: Session):
    repository = _make_repository(db_session)
    db_session.commit()
    client = TestClient(_build_test_app(db_session))

    response = client.get(
        f"/repositories/{repository.id}/files/preview",
        params={"path": "src/app.py", "line": 0},
    )

    assert response.status_code == 422
