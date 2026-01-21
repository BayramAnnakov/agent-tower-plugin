"""Council mode models."""

from typing import Optional
from pydantic import BaseModel, Field


class CouncilOpinion(BaseModel):
    """Opinion from a council member."""

    agent_id: str = Field(description="ID of the council member")
    opinion: str = Field(description="Full opinion text")
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0-1.0)"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points from the opinion"
    )

    @property
    def is_high_confidence(self) -> bool:
        """Check if opinion has high confidence (>0.8)."""
        return self.confidence > 0.8

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "opinion": self.opinion,
            "confidence": self.confidence,
            "key_points": self.key_points,
        }


class PeerRanking(BaseModel):
    """Ranking of peer responses by a council member."""

    reviewer_id: str = Field(description="ID of the reviewer")
    rankings: dict[str, int] = Field(
        default_factory=dict,
        description="Anonymized ID to rank mapping (1=best)"
    )
    reasoning: dict[str, str] = Field(
        default_factory=dict,
        description="Reasoning for each ranking"
    )

    def get_top_ranked(self, n: int = 1) -> list[str]:
        """Get the top N ranked response IDs."""
        sorted_ids = sorted(self.rankings.keys(), key=lambda k: self.rankings[k])
        return sorted_ids[:n]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "reviewer_id": self.reviewer_id,
            "rankings": self.rankings,
            "reasoning": self.reasoning,
        }


class CouncilSynthesis(BaseModel):
    """Final synthesis from the council chairman."""

    chairman_id: str = Field(description="ID of the chairman agent")
    final_answer: str = Field(description="Synthesized final answer")
    consensus_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Level of consensus among council members"
    )
    dissenting_views: list[str] = Field(
        default_factory=list,
        description="Notable dissenting views"
    )
    key_insights: list[str] = Field(
        default_factory=list,
        description="Key insights from the council"
    )

    @property
    def has_strong_consensus(self) -> bool:
        """Check if council reached strong consensus (>0.8)."""
        return self.consensus_level > 0.8

    @property
    def has_dissent(self) -> bool:
        """Check if there are dissenting views."""
        return len(self.dissenting_views) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "chairman_id": self.chairman_id,
            "final_answer": self.final_answer,
            "consensus_level": self.consensus_level,
            "dissenting_views": self.dissenting_views,
            "key_insights": self.key_insights,
        }


class CouncilResult(BaseModel):
    """Complete result of a council deliberation."""

    task: str = Field(description="Original task/question")
    opinions: dict[str, CouncilOpinion] = Field(
        default_factory=dict,
        description="Opinions by agent ID"
    )
    rankings: list[PeerRanking] = Field(
        default_factory=list,
        description="Peer rankings from all members"
    )
    synthesis: Optional[CouncilSynthesis] = Field(
        default=None,
        description="Final synthesis"
    )

    @property
    def member_count(self) -> int:
        """Number of council members who participated."""
        return len(self.opinions)

    def get_aggregate_rankings(self) -> dict[str, float]:
        """Calculate aggregate ranking scores (lower is better)."""
        scores: dict[str, list[int]] = {}
        for ranking in self.rankings:
            for agent_id, rank in ranking.rankings.items():
                if agent_id not in scores:
                    scores[agent_id] = []
                scores[agent_id].append(rank)

        return {
            agent_id: sum(ranks) / len(ranks)
            for agent_id, ranks in scores.items()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task": self.task,
            "member_count": self.member_count,
            "opinions": {k: v.to_dict() for k, v in self.opinions.items()},
            "rankings": [r.to_dict() for r in self.rankings],
            "aggregate_rankings": self.get_aggregate_rankings(),
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
        }
