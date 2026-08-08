"""Tests for the OpenRouter LLM adapter, entirely network-free."""

import json

import httpx
import pytest
from pydantic import SecretStr

from tests.conftest import make_mock_http_client
from vibeguard.adapters.llm.openrouter_client import (
    LlmApiUnavailableError,
    LlmAuthOrQuotaError,
    LlmResponseParseError,
    confirm_findings,
)
from vibeguard.core.finding import FindingSource
from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.heuristics.run_heuristics import HeuristicScanResult
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory

_API_KEY = SecretStr("test-key")


def _openrouter_response(findings_payload: list[dict]) -> httpx.Response:
    body = json.dumps({"findings": findings_payload})
    return httpx.Response(
        200, json={"choices": [{"message": {"content": body}}]}
    )


def _heuristic_result() -> HeuristicScanResult:
    return HeuristicScanResult(
        relative_path="app.py",
        categories=(VulnCategory.INJECTION,),
        hits=(HeuristicHit(VulnCategory.INJECTION, 3, 'cursor.execute(f"...")'),),
    )


def test_confirm_findings_happy_path_returns_findings():
    def handler(request: httpx.Request) -> httpx.Response:
        return _openrouter_response(
            [
                {
                    "category": "injection",
                    "severity": "high",
                    "line_number": 3,
                    "title": "SQL injection via f-string",
                    "description": "User input is interpolated directly into a query.",
                    "remediation": "Use parameterized queries.",
                }
            ]
        )

    client = make_mock_http_client(handler)
    findings = confirm_findings(
        _heuristic_result(),
        content='cursor.execute(f"SELECT * FROM t WHERE id = {x}")',
        client=client,
        api_key=_API_KEY,
        model="deepseek/deepseek-chat-v3.1",
        timeout_seconds=30.0,
        max_tokens=1024,
    )

    assert len(findings) == 1
    assert findings[0].category == VulnCategory.INJECTION
    assert findings[0].severity == Severity.HIGH
    assert findings[0].relative_path == "app.py"
    assert findings[0].source == FindingSource.HEURISTIC_CONFIRMED
    assert findings[0].model == "deepseek/deepseek-chat-v3.1"


def test_confirm_findings_empty_findings_array_is_valid():
    def handler(request: httpx.Request) -> httpx.Response:
        return _openrouter_response([])

    client = make_mock_http_client(handler)
    findings = confirm_findings(
        _heuristic_result(),
        content="safe code",
        client=client,
        api_key=_API_KEY,
        model="deepseek/deepseek-chat-v3.1",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    assert findings == []


def test_confirm_findings_strips_markdown_fence():
    def handler(request: httpx.Request) -> httpx.Response:
        fenced = "```json\n" + json.dumps({"findings": []}) + "\n```"
        return httpx.Response(200, json={"choices": [{"message": {"content": fenced}}]})

    client = make_mock_http_client(handler)
    findings = confirm_findings(
        _heuristic_result(),
        content="x",
        client=client,
        api_key=_API_KEY,
        model="m",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    assert findings == []


def test_confirm_findings_missing_required_field_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return _openrouter_response([{"category": "injection", "severity": "high"}])

    client = make_mock_http_client(handler)
    with pytest.raises(LlmResponseParseError):
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_confirm_findings_invalid_category_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return _openrouter_response(
            [
                {
                    "category": "not_a_real_category",
                    "severity": "high",
                    "line_number": 1,
                    "title": "t",
                    "description": "d",
                    "remediation": "r",
                }
            ]
        )

    client = make_mock_http_client(handler)
    with pytest.raises(LlmResponseParseError):
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_confirm_findings_malformed_json_content_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = make_mock_http_client(handler)
    with pytest.raises(LlmResponseParseError):
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_confirm_findings_unexpected_response_shape_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = make_mock_http_client(handler)
    with pytest.raises(LlmResponseParseError):
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_confirm_findings_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    client = make_mock_http_client(handler)
    with pytest.raises(LlmApiUnavailableError) as excinfo:
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )
    assert excinfo.value.status_code == 503


@pytest.mark.parametrize("status_code", [401, 402, 403, 429])
def test_confirm_findings_auth_or_quota_status_raises_distinct_error(status_code: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="secret leaked upstream detail, do not log me")

    client = make_mock_http_client(handler)
    with pytest.raises(LlmAuthOrQuotaError) as excinfo:
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )

    assert excinfo.value.status_code == status_code
    # code-security: the exception message carries the status code, never
    # the response body text.
    assert "secret leaked upstream detail" not in str(excinfo.value)


def test_confirm_findings_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_http_client(handler)
    with pytest.raises(LlmApiUnavailableError):
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_confirm_findings_non_200_non_5xx_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    client = make_mock_http_client(handler)
    with pytest.raises(LlmResponseParseError) as excinfo:
        confirm_findings(
            _heuristic_result(),
            content="x",
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )
    assert excinfo.value.status_code == 400


def test_confirm_findings_sends_authorization_header_with_unwrapped_key():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return _openrouter_response([])

    client = make_mock_http_client(handler)
    confirm_findings(
        _heuristic_result(),
        content="x",
        client=client,
        api_key=SecretStr("sk-or-real-value"),
        model="m",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    assert seen_headers["authorization"] == "Bearer sk-or-real-value"


def test_confirm_findings_sends_requested_model_and_max_tokens():
    seen_bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _openrouter_response([])

    client = make_mock_http_client(handler)
    confirm_findings(
        _heuristic_result(),
        content="x",
        client=client,
        api_key=_API_KEY,
        model="deepseek/deepseek-chat-v3.1",
        timeout_seconds=30.0,
        max_tokens=777,
    )
    assert seen_bodies[0]["model"] == "deepseek/deepseek-chat-v3.1"
    assert seen_bodies[0]["max_tokens"] == 777
