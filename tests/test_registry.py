#!/usr/bin/env python3
"""Tests for agent registry.

Cross-platform compatible (Windows, macOS, Linux).
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from registry import AGENTS, get_agent, list_agents, register_agent
from base import AgentBackend
from response import AgentResponse, AgentRole


class TestRegistry:
    """Tests for agent registry."""

    def test_agents_registered(self):
        """Test that default agents are registered."""
        assert "claude" in AGENTS
        assert "codex" in AGENTS
        assert "gemini" in AGENTS

    def test_list_agents(self):
        """Test listing registered agents."""
        agents = list_agents()
        assert "claude" in agents
        assert "codex" in agents
        assert "gemini" in agents

    def test_get_agent(self):
        """Test getting an agent by name."""
        agent = get_agent("claude")
        assert agent.name == "claude"

    def test_get_unknown_agent(self):
        """Test that getting unknown agent raises error."""
        with pytest.raises(ValueError) as exc_info:
            get_agent("unknown_agent")
        assert "Unknown agent" in str(exc_info.value)

    def test_register_custom_agent(self):
        """Test registering a custom agent."""
        class MockBackend(AgentBackend):
            name = "mock"

            async def invoke(self, prompt, context=None, role=AgentRole.COUNCIL_MEMBER, status_callback=None):
                return AgentResponse(
                    agent_id=self.name,
                    role=role,
                    content="Mock response",
                )

            async def health_check(self):
                return True

        register_agent("mock", MockBackend)
        assert "mock" in AGENTS

        agent = get_agent("mock")
        assert agent.name == "mock"

        # Clean up
        del AGENTS["mock"]

    def test_register_invalid_agent(self):
        """Test that registering non-AgentBackend raises error."""
        class NotAnAgent:
            pass

        with pytest.raises(TypeError):
            register_agent("invalid", NotAnAgent)


class TestBackendInstantiation:
    """Tests for backend instantiation."""

    def test_claude_backend_defaults(self):
        """Test Claude backend with defaults."""
        agent = get_agent("claude")
        assert agent.model == "opus"
        assert agent.max_turns == 25
        assert agent.timeout == 600

    def test_claude_backend_custom(self):
        """Test Claude backend with custom settings."""
        agent = get_agent("claude", model="sonnet", timeout=300)
        assert agent.model == "sonnet"
        assert agent.timeout == 300

    def test_codex_backend_defaults(self):
        """Test Codex backend with defaults."""
        agent = get_agent("codex")
        assert agent.timeout == 300
        # Default is False for security; CODEX_FULL_DISK_READ env var can enable
        assert agent.full_disk_read is False

    def test_gemini_backend_defaults(self):
        """Test Gemini backend with defaults."""
        agent = get_agent("gemini")
        assert agent.model == "gemini-3-pro-preview"
        assert agent.timeout == 600
        assert agent.sandbox is True
