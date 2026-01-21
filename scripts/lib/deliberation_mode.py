"""Deliberation mode - sequential producer/reviewer rounds (no Rich UI)."""

import json
import logging
import sys
import time
from typing import Optional
from dataclasses import dataclass, asdict

from base import AgentBackend
from response import AgentRole

logger = logging.getLogger(__name__)


def format_elapsed(start_time: float) -> str:
    """Format elapsed time as MM:SS."""
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)
    return f"{mins}:{secs:02d}"


@dataclass
class DeliberationResult:
    """Result of a deliberation session."""

    status: str  # "consensus", "max_rounds", or "error"
    rounds: int
    agreement_level: Optional[float]
    history: list[dict]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


REVIEW_PROMPT = """You are reviewing the following response to a task. Provide structured feedback.

TASK: {task}

RESPONSE TO REVIEW:
{response}

Analyze the response and provide structured feedback. Be constructive and specific.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "overall_assessment": "Brief summary of the response quality",
  "points": [
    {{
      "id": "1",
      "category": "logic|style|security|performance|idea|feasibility",
      "severity": "critical|major|minor|suggestion",
      "description": "Specific feedback",
      "suggested_fix": "How to address this (optional)"
    }}
  ],
  "agreement_level": 0.0-1.0,
  "reasoning": "Why you gave this agreement level"
}}
"""


RESPONSE_PROMPT = """You received feedback on your response. Address each point.

ORIGINAL TASK: {task}

YOUR RESPONSE:
{original_response}

FEEDBACK RECEIVED:
{feedback}

For each feedback point:
- If you agree, explain what you would change
- If you disagree, explain your reasoning

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "agreed_points": ["1", "2"],
  "disputed_points": ["3"],
  "rationale": {{
    "3": "Reason for disagreement"
  }},
  "implemented_changes": ["Description of what you would change"]
}}
"""


class DeliberationMode:
    """Two-agent deliberation with sequential rounds until consensus."""

    def __init__(
        self,
        producer: AgentBackend,
        reviewer: AgentBackend,
        max_rounds: int = 5,
        consensus_threshold: float = 0.85,
        verbose: bool = False,
    ):
        """Initialize deliberation mode.

        Args:
            producer: Agent that generates initial response and responds to feedback
            reviewer: Agent that reviews and provides feedback
            max_rounds: Maximum number of deliberation rounds
            consensus_threshold: Agreement level threshold for consensus (0.0-1.0)
            verbose: Whether to print progress to stderr
        """
        self.producer = producer
        self.reviewer = reviewer
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.verbose = verbose
        self.history: list[dict] = []

    def _log(self, msg: str):
        """Log message to stderr if verbose."""
        if self.verbose:
            print(msg, file=sys.stderr)

    async def run(self, task: str) -> DeliberationResult:
        """Run deliberation until consensus or max rounds.

        Args:
            task: Free-form task description

        Returns:
            DeliberationResult with status, rounds, and history
        """
        start_time = time.time()
        logger.info(f"Starting deliberation: producer={self.producer.name}, reviewer={self.reviewer.name}")

        self._log(f"Deliberation: producer={self.producer.name}, reviewer={self.reviewer.name}")

        # Round 1: Producer initial response
        self._log(f"\n[Round 1/{self.max_rounds}] {self.producer.name} analyzing...")

        round_start = time.time()
        producer_response = await self.producer.invoke(task, role=AgentRole.PRODUCER)
        round_time = format_elapsed(round_start)

        if producer_response.is_error:
            logger.error(f"Producer error: {producer_response.error_message}")
            return DeliberationResult(
                status="error",
                rounds=1,
                agreement_level=None,
                history=self.history,
                error=producer_response.error_message,
            )

        self.history.append({
            "round": 1,
            "agent": self.producer.name,
            "type": "initial",
            "content": producer_response.content,
        })

        self._log(f"  Response received ({len(producer_response.content)} chars, {round_time})")

        # Subsequent rounds: Review -> Response -> Check consensus
        for round_num in range(2, self.max_rounds + 1):
            # Reviewer feedback
            self._log(f"\n[Round {round_num}/{self.max_rounds}] {self.reviewer.name} reviewing...")

            review_prompt = REVIEW_PROMPT.format(
                task=task,
                response=producer_response.content,
            )

            round_start = time.time()
            review_response = await self.reviewer.invoke(review_prompt, role=AgentRole.REVIEWER)
            round_time = format_elapsed(round_start)

            if review_response.is_error:
                logger.error(f"Review error in round {round_num}: {review_response.error_message}")
                self._log(f"  Review error: {review_response.error_message}")
                continue

            feedback = self._parse_json(review_response.content)
            self.history.append({
                "round": round_num,
                "agent": self.reviewer.name,
                "type": "review",
                "content": review_response.content,
                "feedback": feedback,
            })

            # Display feedback summary
            if feedback:
                points = feedback.get("points", [])
                counts = {}
                for point in points:
                    severity = point.get("severity", "unknown")
                    counts[severity] = counts.get(severity, 0) + 1

                parts = []
                for severity in ["critical", "major", "minor", "suggestion"]:
                    if severity in counts:
                        parts.append(f"{counts[severity]} {severity}")

                self._log(f"  Review complete ({round_time})")
                if points:
                    self._log(f"    Found {len(points)} points: {', '.join(parts)}")

                agreement = feedback.get("agreement_level", 0)
                self._log(f"    Agreement level: {agreement:.0%}")

                # Check consensus
                if agreement >= self.consensus_threshold:
                    total_time = format_elapsed(start_time)
                    self._log(f"\nConsensus reached at round {round_num} (agreement: {agreement:.0%}, total: {total_time})")
                    return DeliberationResult(
                        status="consensus",
                        rounds=round_num,
                        agreement_level=agreement,
                        history=self.history,
                    )

            # Producer response to feedback
            self._log(f"\n[Round {round_num}/{self.max_rounds}] {self.producer.name} responding to feedback...")

            response_prompt = RESPONSE_PROMPT.format(
                task=task,
                original_response=producer_response.content,
                feedback=review_response.content,
            )

            round_start = time.time()
            producer_response = await self.producer.invoke(response_prompt, role=AgentRole.PRODUCER)
            round_time = format_elapsed(round_start)

            if producer_response.is_error:
                logger.error(f"Response error in round {round_num}: {producer_response.error_message}")
                self._log(f"  Response error: {producer_response.error_message}")
                continue

            response_data = self._parse_json(producer_response.content)
            self.history.append({
                "round": round_num,
                "agent": self.producer.name,
                "type": "response",
                "content": producer_response.content,
                "response_data": response_data,
            })

            # Display response summary
            if response_data:
                agreed = len(response_data.get("agreed_points", []))
                disputed = len(response_data.get("disputed_points", []))
                changes = response_data.get("implemented_changes", [])

                self._log(f"  Response complete ({round_time})")
                if agreed:
                    self._log(f"    Agreed: {agreed} points")
                if disputed:
                    self._log(f"    Disputed: {disputed} points")
                if changes:
                    self._log(f"    Proposed changes: {len(changes)}")

        total_time = format_elapsed(start_time)
        self._log(f"\nMax rounds ({self.max_rounds}) reached without consensus (total: {total_time})")

        return DeliberationResult(
            status="max_rounds",
            rounds=self.max_rounds,
            agreement_level=feedback.get("agreement_level") if feedback else None,
            history=self.history,
        )

    def _parse_json(self, content: str) -> Optional[dict]:
        """Parse JSON from content, with fallback."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            if start == -1:
                return None

            depth = 0
            for i, char in enumerate(content[start:], start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(content[start : i + 1])
                        except json.JSONDecodeError:
                            return None

            return None
