#!/usr/bin/env python3
"""Tests for model classes.

Cross-platform compatible (Windows, macOS, Linux).
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from response import AgentResponse, AgentRole
from council import CouncilOpinion, PeerRanking, CouncilSynthesis, CouncilResult
from feedback import FeedbackPoint, ReviewFeedback, ProducerResponse


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_create_response(self):
        """Test creating a basic agent response."""
        response = AgentResponse(
            agent_id="claude",
            role=AgentRole.COUNCIL_MEMBER,
            content="Test response",
        )
        assert response.agent_id == "claude"
        assert response.role == AgentRole.COUNCIL_MEMBER
        assert response.content == "Test response"
        assert response.is_error is False

    def test_error_response(self):
        """Test error detection in response."""
        response = AgentResponse(
            agent_id="codex",
            role=AgentRole.REVIEWER,
            content="[Error: Timeout]",
            metadata={"error": "timeout"},
        )
        assert response.is_error is True
        assert response.error_message == "timeout"

    def test_to_dict(self):
        """Test serialization to dict."""
        response = AgentResponse(
            agent_id="gemini",
            role=AgentRole.CHAIRMAN,
            content="Final answer",
            metadata={"model": "gemini-3-pro"},
        )
        d = response.to_dict()
        assert d["agent_id"] == "gemini"
        assert d["role"] == "chairman"
        assert d["content"] == "Final answer"
        assert d["is_error"] is False


class TestCouncilOpinion:
    """Tests for CouncilOpinion model."""

    def test_create_opinion(self):
        """Test creating an opinion."""
        opinion = CouncilOpinion(
            agent_id="claude",
            opinion="This is my analysis",
            confidence=0.85,
            key_points=["point 1", "point 2"],
        )
        assert opinion.agent_id == "claude"
        assert opinion.confidence == 0.85
        assert opinion.is_high_confidence is True

    def test_low_confidence(self):
        """Test low confidence detection."""
        opinion = CouncilOpinion(
            agent_id="codex",
            opinion="Not sure about this",
            confidence=0.5,
        )
        assert opinion.is_high_confidence is False

    def test_to_dict(self):
        """Test serialization."""
        opinion = CouncilOpinion(
            agent_id="gemini",
            opinion="My opinion",
            confidence=0.9,
            key_points=["a", "b"],
        )
        d = opinion.to_dict()
        assert d["agent_id"] == "gemini"
        assert d["confidence"] == 0.9
        assert d["key_points"] == ["a", "b"]


class TestPeerRanking:
    """Tests for PeerRanking model."""

    def test_create_ranking(self):
        """Test creating a peer ranking."""
        ranking = PeerRanking(
            reviewer_id="claude",
            rankings={"A": 1, "B": 2, "C": 3},
            reasoning={"A": "Best analysis"},
        )
        assert ranking.reviewer_id == "claude"
        assert ranking.rankings["A"] == 1

    def test_get_top_ranked(self):
        """Test getting top ranked responses."""
        ranking = PeerRanking(
            reviewer_id="claude",
            rankings={"A": 2, "B": 1, "C": 3},
        )
        top = ranking.get_top_ranked(2)
        assert top == ["B", "A"]


class TestCouncilSynthesis:
    """Tests for CouncilSynthesis model."""

    def test_create_synthesis(self):
        """Test creating a synthesis."""
        synthesis = CouncilSynthesis(
            chairman_id="claude",
            final_answer="The consensus is...",
            consensus_level=0.85,
            dissenting_views=["One agent disagreed"],
            key_insights=["insight 1"],
        )
        assert synthesis.chairman_id == "claude"
        assert synthesis.has_strong_consensus is True
        assert synthesis.has_dissent is True

    def test_no_consensus(self):
        """Test weak consensus detection."""
        synthesis = CouncilSynthesis(
            chairman_id="claude",
            final_answer="No agreement",
            consensus_level=0.4,
        )
        assert synthesis.has_strong_consensus is False
        assert synthesis.has_dissent is False


class TestCouncilResult:
    """Tests for CouncilResult model."""

    def test_create_result(self):
        """Test creating a full council result."""
        opinion = CouncilOpinion(
            agent_id="claude",
            opinion="My opinion",
            confidence=0.8,
        )
        result = CouncilResult(
            task="Test task",
            opinions={"claude": opinion},
        )
        assert result.task == "Test task"
        assert result.member_count == 1

    def test_to_dict(self):
        """Test serialization of full result."""
        opinion = CouncilOpinion(
            agent_id="claude",
            opinion="My opinion",
            confidence=0.8,
        )
        synthesis = CouncilSynthesis(
            chairman_id="claude",
            final_answer="Final",
            consensus_level=0.9,
        )
        result = CouncilResult(
            task="Test task",
            opinions={"claude": opinion},
            synthesis=synthesis,
        )
        d = result.to_dict()
        assert d["task"] == "Test task"
        assert d["member_count"] == 1
        assert d["synthesis"]["consensus_level"] == 0.9


class TestFeedbackModels:
    """Tests for feedback models."""

    def test_feedback_point(self):
        """Test creating a feedback point."""
        point = FeedbackPoint(
            id="1",
            category="security",
            severity="critical",
            description="SQL injection vulnerability",
            suggested_fix="Use parameterized queries",
        )
        assert point.is_critical is True
        assert point.is_actionable is True

    def test_review_feedback(self):
        """Test creating review feedback."""
        point = FeedbackPoint(
            id="1",
            category="logic",
            severity="major",
            description="Off by one error",
        )
        feedback = ReviewFeedback(
            overall_assessment="Good but needs fixes",
            points=[point],
            agreement_level=0.7,
        )
        assert feedback.has_critical_issues is False
        assert feedback.point_count_by_severity == {"major": 1}

    def test_producer_response(self):
        """Test creating producer response."""
        response = ProducerResponse(
            agreed_points=["1", "2"],
            disputed_points=["3"],
            rationale={"3": "I disagree because..."},
            implemented_changes=["Fixed issue 1"],
        )
        assert response.agreement_ratio == 2/3
        assert response.has_disputes is True
