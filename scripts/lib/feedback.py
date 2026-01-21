"""Feedback models for deliberation mode."""

from typing import Optional
from pydantic import BaseModel, Field


class FeedbackPoint(BaseModel):
    """A single feedback point from a reviewer."""

    id: str = Field(description="Unique identifier for this point")
    category: str = Field(
        description="Category: logic, style, security, performance, idea, feasibility"
    )
    severity: str = Field(
        description="Severity: critical, major, minor, suggestion"
    )
    description: str = Field(description="Description of the feedback")
    location: Optional[str] = Field(
        default=None,
        description="Location reference (e.g., file:line)"
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Suggested fix or improvement"
    )

    @property
    def is_critical(self) -> bool:
        """Check if this is a critical issue."""
        return self.severity == "critical"

    @property
    def is_actionable(self) -> bool:
        """Check if this feedback has a suggested fix."""
        return self.suggested_fix is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "location": self.location,
            "suggested_fix": self.suggested_fix,
        }


class ReviewFeedback(BaseModel):
    """Structured feedback from a reviewer."""

    overall_assessment: str = Field(description="Overall assessment summary")
    points: list[FeedbackPoint] = Field(
        default_factory=list,
        description="List of feedback points"
    )
    agreement_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Agreement level with the reviewed content (0.0-1.0)"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Reasoning behind the assessment"
    )

    @property
    def has_critical_issues(self) -> bool:
        """Check if feedback contains critical issues."""
        return any(p.is_critical for p in self.points)

    @property
    def point_count_by_severity(self) -> dict[str, int]:
        """Count points by severity."""
        counts: dict[str, int] = {}
        for point in self.points:
            counts[point.severity] = counts.get(point.severity, 0) + 1
        return counts

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_assessment": self.overall_assessment,
            "points": [p.to_dict() for p in self.points],
            "agreement_level": self.agreement_level,
            "reasoning": self.reasoning,
            "point_count_by_severity": self.point_count_by_severity,
        }


class ProducerResponse(BaseModel):
    """Response from a producer addressing reviewer feedback."""

    agreed_points: list[str] = Field(
        default_factory=list,
        description="IDs of feedback points the producer agrees with"
    )
    disputed_points: list[str] = Field(
        default_factory=list,
        description="IDs of feedback points the producer disputes"
    )
    rationale: dict[str, str] = Field(
        default_factory=dict,
        description="Reasoning for disputed points (point_id -> reason)"
    )
    implemented_changes: list[str] = Field(
        default_factory=list,
        description="Descriptions of changes made"
    )

    @property
    def agreement_ratio(self) -> float:
        """Calculate the ratio of agreed to total points."""
        total = len(self.agreed_points) + len(self.disputed_points)
        if total == 0:
            return 1.0
        return len(self.agreed_points) / total

    @property
    def has_disputes(self) -> bool:
        """Check if there are any disputed points."""
        return len(self.disputed_points) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agreed_points": self.agreed_points,
            "disputed_points": self.disputed_points,
            "rationale": self.rationale,
            "implemented_changes": self.implemented_changes,
            "agreement_ratio": self.agreement_ratio,
        }
