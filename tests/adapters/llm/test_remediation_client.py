"""Tests for the remediation-generation LLM adapter, entirely network-free."""

import json

import httpx
import pytest
from pydantic import SecretStr

from tests.conftest import make_mock_http_client
from vibeguard.adapters.llm.remediation_client import (
    RemediationResponseParseError,
    RemediationUnavailableError,
    generate_remediation,
)
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory

_API_KEY = SecretStr("test-key")


def _openrouter_response(proposed_content: str, summary: str) -> httpx.Response:
    body = json.dumps({"proposed_content": proposed_content, "summary": summary})
    return httpx.Response(200, json={"choices": [{"message": {"content": body}}]})


def _finding() -> Finding:
    return Finding(
        category=VulnCategory.INJECTION,
        severity=Severity.HIGH,
        title="SQL injection via f-string",
        description="User input is interpolated directly into a query.",
        remediation="Use parameterized queries.",
        relative_path="app.py",
        line_number=3,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="deepseek/deepseek-chat-v3.1",
    )


def test_generate_remediation_happy_path_returns_proposal():
    def handler(request: httpx.Request) -> httpx.Response:
        return _openrouter_response("cursor.execute(query, (x,))", "Parameterized the query.")

    client = make_mock_http_client(handler)
    result = generate_remediation(
        relative_path="app.py",
        content='cursor.execute(f"SELECT * FROM t WHERE id = {x}")',
        findings=[_finding()],
        client=client,
        api_key=_API_KEY,
        model="deepseek/deepseek-chat-v3.1",
        timeout_seconds=30.0,
        max_tokens=1024,
    )

    assert result.proposed_content == "cursor.execute(query, (x,))"
    assert result.summary == "Parameterized the query."


def test_generate_remediation_strips_markdown_fence():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.dumps({"proposed_content": "fixed", "summary": "s"})
        fenced = "```json\n" + payload + "\n```"
        return httpx.Response(200, json={"choices": [{"message": {"content": fenced}}]})

    client = make_mock_http_client(handler)
    result = generate_remediation(
        relative_path="app.py",
        content="x",
        findings=[_finding()],
        client=client,
        api_key=_API_KEY,
        model="m",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    assert result.proposed_content == "fixed"


def test_generate_remediation_missing_required_field_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.dumps({"summary": "s"})
        return httpx.Response(200, json={"choices": [{"message": {"content": body}}]})

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationResponseParseError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_malformed_json_content_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationResponseParseError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_unexpected_response_shape_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationResponseParseError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationUnavailableError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationUnavailableError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_non_200_non_5xx_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    client = make_mock_http_client(handler)
    with pytest.raises(RemediationResponseParseError):
        generate_remediation(
            relative_path="app.py",
            content="x",
            findings=[_finding()],
            client=client,
            api_key=_API_KEY,
            model="m",
            timeout_seconds=30.0,
            max_tokens=1024,
        )


def test_generate_remediation_sends_authorization_header_with_unwrapped_key():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return _openrouter_response("fixed", "s")

    client = make_mock_http_client(handler)
    generate_remediation(
        relative_path="app.py",
        content="x",
        findings=[_finding()],
        client=client,
        api_key=SecretStr("sk-or-real-value"),
        model="m",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    assert seen_headers["authorization"] == "Bearer sk-or-real-value"


def test_generate_remediation_sends_requested_model_and_max_tokens():
    seen_bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _openrouter_response("fixed", "s")

    client = make_mock_http_client(handler)
    generate_remediation(
        relative_path="app.py",
        content="x",
        findings=[_finding()],
        client=client,
        api_key=_API_KEY,
        model="deepseek/deepseek-chat-v3.1",
        timeout_seconds=30.0,
        max_tokens=777,
    )
    assert seen_bodies[0]["model"] == "deepseek/deepseek-chat-v3.1"
    assert seen_bodies[0]["max_tokens"] == 777


def test_generate_remediation_prompt_includes_finding_and_guidance_details():
    seen_bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return _openrouter_response("fixed", "s")

    client = make_mock_http_client(handler)
    generate_remediation(
        relative_path="app.py",
        content="original content",
        findings=[_finding()],
        client=client,
        api_key=_API_KEY,
        model="m",
        timeout_seconds=30.0,
        max_tokens=1024,
    )
    user_message = seen_bodies[0]["messages"][1]["content"]
    assert "SQL injection via f-string" in user_message
    assert "injection" in user_message
    assert "original content" in user_message
    assert "<FILE_CONTENT>" in user_message
