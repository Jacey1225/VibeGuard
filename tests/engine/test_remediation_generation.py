"""Tests for the remediation-generation orchestration."""

import threading
import time
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

import vibeguard.engine.remediation_generation as remediation_generation_module
from vibeguard.adapters.db.finding_store import insert_findings
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.adapters.llm.remediation_client import (
    GeneratedRemediation,
    RemediationUnavailableError,
)
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.remediation_generation import (
    RepositoryNotFoundError,
    RepositoryNotReadyForRemediationError,
    generate_remediations_for_repository,
)


def _make_repository(
    session: Session, status: RepositoryStatus = RepositoryStatus.SCANNED
) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="o", name="r", status=status)
    session.add(repository)
    session.flush()
    return repository


def _add_file(
    session: Session, repository: RepositoryModel, relative_path: str, content: str
) -> None:
    session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path=relative_path,
            size_bytes=len(content),
            content=content,
        )
    )


def _add_finding(
    session: Session,
    repository: RepositoryModel,
    relative_path: str,
    category: VulnCategory = VulnCategory.INJECTION,
) -> None:
    finding = Finding(
        category=category,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path=relative_path,
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )
    insert_findings(session, repository.id, [finding])


def test_generate_remediations_missing_repository_raises(db_session: Session, settings_factory):
    with pytest.raises(RepositoryNotFoundError):
        generate_remediations_for_repository(
            999_999, db_session, llm_client=object(), settings=settings_factory()
        )


def test_generate_remediations_repository_not_scanned_raises(
    db_session: Session, settings_factory
):
    repository = _make_repository(db_session, status=RepositoryStatus.SCANNING)
    db_session.flush()

    with pytest.raises(RepositoryNotReadyForRemediationError):
        generate_remediations_for_repository(
            repository.id, db_session, llm_client=object(), settings=settings_factory()
        )


def test_generate_remediations_no_findings_returns_empty_outcome(
    db_session: Session, settings_factory
):
    repository = _make_repository(db_session)
    db_session.flush()

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    assert outcome.remediations == []
    assert outcome.attempted == 0
    assert outcome.succeeded == 0


def test_generate_remediations_groups_multiple_findings_same_file_into_one_call(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "original content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py", VulnCategory.INJECTION)
    _add_finding(db_session, repository, "app.py", VulnCategory.CRYPTO_FAILURES)
    db_session.flush()

    call_spy = Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s"))
    monkeypatch.setattr(remediation_generation_module, "generate_remediation", call_spy)

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    assert call_spy.call_count == 1
    findings_arg = call_spy.call_args.args[2]
    assert len(findings_arg) == 2
    assert outcome.attempted == 1
    assert outcome.succeeded == 1
    assert len(outcome.remediations) == 1


def test_generate_remediations_persists_remediation_fields(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "original content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py")
    db_session.flush()

    monkeypatch.setattr(
        remediation_generation_module,
        "generate_remediation",
        Mock(return_value=GeneratedRemediation(proposed_content="fixed content", summary="s")),
    )

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    assert len(outcome.remediations) == 1
    remediation = outcome.remediations[0]
    assert remediation.relative_path == "app.py"
    assert remediation.original_content == "original content"
    assert remediation.proposed_content == "fixed content"
    assert remediation.summary == "s"
    assert "original content" in remediation.diff_text
    assert "fixed content" in remediation.diff_text


def test_generate_remediations_one_failing_call_does_not_abort_the_rest(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "a.py", "content a")
    _add_file(db_session, repository, "b.py", "content b")
    db_session.flush()
    _add_finding(db_session, repository, "a.py")
    _add_finding(db_session, repository, "b.py")
    db_session.flush()

    def fake_generate_remediation(
        relative_path, content, findings, client, api_key, model, timeout_seconds, max_tokens
    ):
        if relative_path == "a.py":
            raise RemediationUnavailableError("simulated")
        return GeneratedRemediation(proposed_content="fixed b", summary="s")

    monkeypatch.setattr(
        remediation_generation_module, "generate_remediation", fake_generate_remediation
    )

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    assert outcome.attempted == 2
    assert outcome.succeeded == 1
    assert len(outcome.remediations) == 1
    assert outcome.remediations[0].relative_path == "b.py"


def test_generate_remediations_caps_llm_calls_and_reports_files_over_cap(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    for i in range(5):
        _add_file(db_session, repository, f"f{i}.py", "content")
    db_session.flush()
    for i in range(5):
        _add_finding(db_session, repository, f"f{i}.py")
    db_session.flush()

    call_spy = Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s"))
    monkeypatch.setattr(remediation_generation_module, "generate_remediation", call_spy)

    settings = settings_factory(max_llm_calls_per_remediation=2)
    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings
    )

    assert call_spy.call_count == 2
    assert outcome.attempted == 2
    assert outcome.files_over_cap == 3


def test_generate_remediations_flags_new_heuristic_hits_in_proposed_content(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "original content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py", VulnCategory.INJECTION)
    db_session.flush()

    # The "fix" introduces a hardcoded secret -- a category never
    # requested -- which the safety net must surface.
    monkeypatch.setattr(
        remediation_generation_module,
        "generate_remediation",
        Mock(
            return_value=GeneratedRemediation(
                proposed_content='API_KEY = "sk_live_abcdef1234567890"', summary="s"
            )
        ),
    )

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    remediation = outcome.remediations[0]
    assert remediation.introduces_new_heuristic_hits is True
    assert "crypto_failures" in (remediation.new_heuristic_hit_summary or "")


def test_generate_remediations_zero_call_budget_admits_nothing(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py")
    db_session.flush()

    call_spy = Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s"))
    monkeypatch.setattr(remediation_generation_module, "generate_remediation", call_spy)

    settings = settings_factory(max_llm_calls_per_remediation=0)
    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings
    )

    call_spy.assert_not_called()
    assert outcome.attempted == 0
    assert outcome.files_over_cap == 1


def test_generate_remediations_skips_finding_with_no_stored_content(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    # Deliberately no _add_file call: the finding references a path
    # with no stored content, e.g. a file removed between scan and
    # remediation.
    _add_finding(db_session, repository, "missing.py")
    db_session.flush()

    call_spy = Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s"))
    monkeypatch.setattr(remediation_generation_module, "generate_remediation", call_spy)

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    call_spy.assert_not_called()
    assert outcome.attempted == 1
    assert outcome.succeeded == 0


def test_generate_remediations_no_new_heuristic_hits_when_category_unchanged(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "original content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py", VulnCategory.INJECTION)
    db_session.flush()

    # The "fix" still contains an injection-shaped pattern -- the same
    # category the finding already addressed, so nothing new.
    monkeypatch.setattr(
        remediation_generation_module,
        "generate_remediation",
        Mock(
            return_value=GeneratedRemediation(
                proposed_content='cursor.execute(f"SELECT * FROM t WHERE id = {x}")', summary="s"
            )
        ),
    )

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    remediation = outcome.remediations[0]
    assert remediation.introduces_new_heuristic_hits is False
    assert remediation.new_heuristic_hit_summary is None


def test_generate_remediations_safety_net_degrades_gracefully_on_exception(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "app.py", "original content")
    db_session.flush()
    _add_finding(db_session, repository, "app.py")
    db_session.flush()

    monkeypatch.setattr(
        remediation_generation_module,
        "generate_remediation",
        Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s")),
    )
    monkeypatch.setattr(
        remediation_generation_module, "run_heuristics", Mock(side_effect=RuntimeError("boom"))
    )

    outcome = generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings_factory()
    )

    remediation = outcome.remediations[0]
    assert remediation.introduces_new_heuristic_hits is False
    assert remediation.new_heuristic_hit_summary is None


def test_generate_remediations_respects_max_concurrent_llm_calls(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    for i in range(9):
        _add_file(db_session, repository, f"f{i}.py", "content")
    db_session.flush()
    for i in range(9):
        _add_finding(db_session, repository, f"f{i}.py")
    db_session.flush()

    lock = threading.Lock()
    active = 0
    max_seen = 0

    def fake_generate_remediation(
        relative_path, content, findings, client, api_key, model, timeout_seconds, max_tokens
    ):
        nonlocal active, max_seen
        with lock:
            active += 1
            max_seen = max(max_seen, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return GeneratedRemediation(proposed_content="fixed", summary="s")

    monkeypatch.setattr(
        remediation_generation_module, "generate_remediation", fake_generate_remediation
    )

    settings = settings_factory(max_concurrent_remediation_llm_calls=3)
    generate_remediations_for_repository(
        repository.id, db_session, llm_client=object(), settings=settings
    )

    assert max_seen <= 3
    assert max_seen > 1
