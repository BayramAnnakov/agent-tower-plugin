#!/usr/bin/env python3
"""Tests for OpenCode backend."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from opencode_backend import OpencodeBackend
from response import AgentRole


class TestOpencodeBackend:
    """Tests for OpencodeBackend class."""

    def test_backend_exists(self):
        """Test that OpencodeBackend can be imported."""
        assert OpencodeBackend is not None

    def test_default_initialization(self):
        """Test backend initializes with defaults."""
        backend = OpencodeBackend()
        assert backend.name == "opencode"
        assert backend.model == "github-copilot/gemini-3-pro-preview"
        assert backend.timeout == 600
        assert backend.agent_id == "gemini-3-pro-preview"

    def test_custom_initialization(self):
        """Test backend initializes with custom values."""
        backend = OpencodeBackend(
            model="github-copilot/gpt-5.1-codex",
            timeout=300,
        )
        assert backend.model == "github-copilot/gpt-5.1-codex"
        assert backend.timeout == 300
        assert backend.agent_id == "gpt-5.1-codex"

    def test_agent_id_extraction(self):
        """Test agent_id is extracted from model path."""
        backend = OpencodeBackend(model="github-copilot/claude-sonnet-4.6")
        assert backend.agent_id == "claude-sonnet-4.6"

        # Model without slash uses full name
        backend2 = OpencodeBackend(model="local-model")
        assert backend2.agent_id == "local-model"


class TestOpencodeHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_cli_not_found(self):
        """Test health check returns False when CLI not installed."""
        backend = OpencodeBackend()
        # This will return False on machines without opencode installed
        result = await backend.health_check()
        # We can't assert True/False since it depends on environment
        # Just verify it returns a boolean without error
        assert isinstance(result, bool)


class TestOpencodeResponseParsing:
    """Tests for JSONL response parsing."""

    def test_parse_text_events(self):
        """Test parsing text events from JSONL output."""
        backend = OpencodeBackend()

        jsonl = '''{"type":"step_start","timestamp":1234,"sessionID":"abc"}
{"type":"text","timestamp":1235,"sessionID":"abc","part":{"text":"Hello "}}
{"type":"text","timestamp":1236,"sessionID":"abc","part":{"text":"world!"}}
{"type":"step_finish","timestamp":1237,"sessionID":"abc","part":{"tokens":{"input":10,"output":5}}}'''

        result = backend._parse_jsonl_response(jsonl)
        assert result == "Hello world!"

    def test_parse_empty_output(self):
        """Test parsing empty output returns empty string."""
        backend = OpencodeBackend()
        assert backend._parse_jsonl_response("") == ""
        assert backend._parse_jsonl_response("   ") == ""

    def test_parse_single_text_event(self):
        """Test parsing single text event."""
        backend = OpencodeBackend()
        jsonl = '{"type":"text","part":{"text":"Single response"}}'
        assert backend._parse_jsonl_response(jsonl) == "Single response"

    def test_parse_invalid_json_lines(self):
        """Test that invalid JSON lines are skipped."""
        backend = OpencodeBackend()
        jsonl = '''{"type":"text","part":{"text":"Valid"}}
not valid json
{"type":"text","part":{"text":" response"}}'''

        result = backend._parse_jsonl_response(jsonl)
        assert result == "Valid response"


class TestOpencodeInvoke:
    """Tests for invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_cli_not_found(self):
        """Test invoke returns error when CLI not installed."""
        backend = OpencodeBackend()
        response = await backend.invoke("test prompt")

        # On machines without opencode, should return error response
        assert response.agent_id == "gemini-3-pro-preview"
        assert response.role == AgentRole.COUNCIL_MEMBER
        # Either succeeds or returns CLI not found error
        if response.is_error:
            assert "not found" in response.content.lower() or "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_invoke_returns_agent_response(self):
        """Test invoke returns proper AgentResponse structure."""
        backend = OpencodeBackend(model="github-copilot/test-model")
        response = await backend.invoke("test prompt", role=AgentRole.PRODUCER)

        assert response.agent_id == "test-model"
        assert response.role == AgentRole.PRODUCER
        assert isinstance(response.content, str)
        assert isinstance(response.metadata, dict)

    def test_command_construction(self):
        """Test that command is constructed correctly."""
        backend = OpencodeBackend(model="github-copilot/gemini-3-pro-preview")
        cmd = backend._build_command("test prompt")

        assert cmd[0] == "opencode"
        assert cmd[1] == "run"
        assert "test prompt" in cmd
        assert "-m" in cmd
        assert "github-copilot/gemini-3-pro-preview" in cmd
        assert "--format" in cmd
        assert "json" in cmd
