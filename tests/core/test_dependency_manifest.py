"""Tests for dependency manifest/lockfile presence detection."""

from vibeguard.core.dependency_manifest import find_dependency_manifest
from vibeguard.core.finding import FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


def test_find_dependency_manifest_detects_requirements_txt():
    finding = find_dependency_manifest(["README.md", "src/app.py", "requirements.txt"])
    assert finding is not None
    assert finding.relative_path == "requirements.txt"
    assert finding.category == VulnCategory.VULNERABLE_DEPENDENCIES
    assert finding.severity == Severity.INFO
    assert finding.source == FindingSource.HEURISTIC_ONLY
    assert finding.line_number is None


def test_find_dependency_manifest_detects_manifest_in_subdirectory():
    finding = find_dependency_manifest(["backend/requirements.txt"])
    assert finding is not None
    assert finding.relative_path == "backend/requirements.txt"


def test_find_dependency_manifest_detects_package_lock_json():
    finding = find_dependency_manifest(["package.json", "package-lock.json"])
    assert finding is not None
    assert finding.relative_path == "package.json"


def test_find_dependency_manifest_returns_none_when_no_manifest_present():
    assert find_dependency_manifest(["README.md", "src/app.py"]) is None


def test_find_dependency_manifest_returns_none_for_empty_repository():
    assert find_dependency_manifest([]) is None
