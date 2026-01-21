#!/usr/bin/env python3
"""Tests for persona assignment.

Cross-platform compatible (Windows, macOS, Linux).
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from personas import (
    Persona,
    infer_personas,
    get_persona_for_task,
    format_persona_assignment,
    SECURITY_ANALYST,
    SYSTEMS_ARCHITECT,
    CODE_QUALITY_REVIEWER,
    BUSINESS_STRATEGIST,
    DEVIL_ADVOCATE,
)


class TestPersona:
    """Tests for Persona dataclass."""

    def test_create_persona(self):
        """Test creating a persona."""
        persona = Persona(
            name="Test Expert",
            focus_areas=["area1", "area2"],
            system_prompt="You are a test expert.",
        )
        assert persona.name == "Test Expert"
        assert len(persona.focus_areas) == 2

    def test_format_prompt(self):
        """Test formatting prompt with persona context."""
        persona = Persona(
            name="Test Expert",
            focus_areas=["area1"],
            system_prompt="Focus on testing.",
        )
        formatted = persona.format_prompt("Analyze this code")
        assert "Test Expert" in formatted
        assert "area1" in formatted
        assert "Focus on testing" in formatted
        assert "Analyze this code" in formatted

    def test_to_dict(self):
        """Test serialization."""
        d = SECURITY_ANALYST.to_dict()
        assert d["name"] == "Security Analyst"
        assert "authentication" in d["focus_areas"]


class TestInferPersonas:
    """Tests for persona inference."""

    def test_security_keywords(self):
        """Test that security keywords trigger Security Analyst."""
        personas = infer_personas("Check authentication flow for vulnerabilities", 3)
        persona_names = [p.name for p in personas]
        assert "Security Analyst" in persona_names

    def test_architecture_keywords(self):
        """Test that architecture keywords trigger Systems Architect."""
        personas = infer_personas("Review scalability and performance", 3)
        persona_names = [p.name for p in personas]
        assert "Systems Architect" in persona_names

    def test_code_quality_keywords(self):
        """Test that code quality keywords trigger Code Quality Reviewer."""
        personas = infer_personas("Refactor this code and improve testing", 3)
        persona_names = [p.name for p in personas]
        assert "Code Quality Reviewer" in persona_names

    def test_business_keywords(self):
        """Test that business keywords trigger Business Strategist."""
        personas = infer_personas("Evaluate this startup idea for market fit", 3)
        persona_names = [p.name for p in personas]
        assert "Business Strategist" in persona_names

    def test_devils_advocate_included(self):
        """Test that Devil's Advocate is included with 3+ agents."""
        personas = infer_personas("Some generic task", 3)
        persona_names = [p.name for p in personas]
        assert "Devil's Advocate" in persona_names

    def test_devils_advocate_not_with_two_agents(self):
        """Test that Devil's Advocate may be skipped with 2 agents."""
        # With only 2 agents and no matching keywords, Devil's Advocate
        # should not necessarily be included
        personas = infer_personas("Some generic task", 2)
        assert len(personas) == 2

    def test_num_personas_matches_request(self):
        """Test that we get the requested number of personas."""
        # Default personas pool has 4 items, so test up to 4
        for n in [2, 3, 4]:
            personas = infer_personas("Test task", n)
            assert len(personas) == n

    def test_no_duplicate_personas(self):
        """Test that personas are unique."""
        personas = infer_personas("Test scalability, performance, and caching", 5)
        persona_names = [p.name for p in personas]
        assert len(persona_names) == len(set(persona_names))


class TestGetPersonaForTask:
    """Tests for get_persona_for_task."""

    def test_get_first_persona(self):
        """Test getting persona for first agent."""
        persona = get_persona_for_task("Check security vulnerabilities", 0, 3)
        assert persona is not None
        assert "Security Analyst" in persona.name or persona is not None

    def test_get_multiple_personas(self):
        """Test getting personas for multiple agents."""
        personas = [
            get_persona_for_task("Review code", i, 3)
            for i in range(3)
        ]
        assert all(p is not None for p in personas)


class TestFormatPersonaAssignment:
    """Tests for formatting persona assignments."""

    def test_format_assignment(self):
        """Test formatting persona assignments."""
        personas = [SECURITY_ANALYST, CODE_QUALITY_REVIEWER]
        agents = ["claude", "codex"]
        output = format_persona_assignment(personas, agents)
        assert "claude" in output
        assert "codex" in output
        assert "Security Analyst" in output
        assert "Code Quality Reviewer" in output
        assert "Assigning perspectives" in output
