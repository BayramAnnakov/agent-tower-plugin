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
