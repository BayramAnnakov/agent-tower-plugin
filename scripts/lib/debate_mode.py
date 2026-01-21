"""Debate mode - adversarial argumentation for binary decisions (no Rich UI)."""

import asyncio
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
class DebateArgument:
    """An argument in the debate."""

    agent_id: str
    position: str  # "pro" or "con"
    round_num: int
    argument: str
    key_points: list[str]
    confidence: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class DebateJudgment:
    """The judge's final verdict."""

    judge_id: str
    winner: str  # "pro" or "con"
    reasoning: str
    score_pro: float  # 0.0-1.0
    score_con: float  # 0.0-1.0
    key_factors: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class DebateResult:
    """Result of a debate session."""

    question: str
    pro_agent: str
    con_agent: str
    arguments: list[DebateArgument]
    judgment: DebateJudgment
    rounds: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "question": self.question,
            "pro_agent": self.pro_agent,
            "con_agent": self.con_agent,
            "arguments": [a.to_dict() for a in self.arguments],
            "judgment": self.judgment.to_dict(),
            "rounds": self.rounds,
        }


OPENING_ARGUMENT_PROMPT = """You are debating the following question. You must argue for the {position} position.

QUESTION: {question}

YOUR POSITION: {position_description}

Make a compelling opening argument for your position. Be persuasive and use evidence, logic, and reasoning.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "argument": "Your full, persuasive argument",
  "key_points": ["Main point 1", "Main point 2", "Main point 3"],
  "confidence": 0.0-1.0
}}
"""


REBUTTAL_PROMPT = """You are debating the following question. You must argue for the {position} position.

QUESTION: {question}

YOUR POSITION: {position_description}

OPPONENT'S ARGUMENT:
{opponent_argument}

Respond to your opponent's argument. Address their key points, provide counterarguments, and strengthen your position.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "argument": "Your rebuttal and continued argument",
  "key_points": ["Rebuttal point 1", "Rebuttal point 2", "New supporting point"],
  "confidence": 0.0-1.0
}}
"""


JUDGE_PROMPT = """You are judging a debate on the following question.

QUESTION: {question}

PRO POSITION (in favor):
{pro_arguments}

CON POSITION (against):
{con_arguments}

Evaluate both sides objectively. Consider:
- Strength of logical arguments
- Quality of evidence and reasoning
- Effectiveness of rebuttals
- Overall persuasiveness

Declare a winner and explain your reasoning.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "winner": "pro" or "con",
  "reasoning": "Detailed explanation of your decision",
  "score_pro": 0.0-1.0,
  "score_con": 0.0-1.0,
  "key_factors": ["Factor that influenced decision 1", "Factor 2", "Factor 3"]
}}
"""


class DebateMode:
    """Adversarial debate mode for binary decisions.

    Two agents argue opposing positions, then a judge evaluates.

    Structure:
    - Round 1: Opening arguments (parallel)
    - Round 2-N: Rebuttals (sequential)
    - Final: Judge evaluates and declares winner
    """

    def __init__(
        self,
        pro_agent: AgentBackend,
        con_agent: AgentBackend,
        judge: Optional[AgentBackend] = None,
        max_rounds: int = 3,
        verbose: bool = False,
    ):
        """Initialize debate mode.

        Args:
            pro_agent: Agent arguing in favor
            con_agent: Agent arguing against
            judge: Agent to judge the debate (defaults to pro_agent)
            max_rounds: Number of argument rounds (including opening)
            verbose: Whether to print progress to stderr
        """
        self.pro_agent = pro_agent
        self.con_agent = con_agent
        self.judge = judge or pro_agent
        self.max_rounds = max_rounds
        self.verbose = verbose
        self.arguments: list[DebateArgument] = []

    def _log(self, msg: str):
        """Log message to stderr if verbose."""
        if self.verbose:
            print(msg, file=sys.stderr)

    async def run(self, question: str) -> DebateResult:
        """Run the debate.

        Args:
            question: The binary decision question to debate

        Returns:
            DebateResult with arguments and judgment
        """
        start_time = time.time()
        logger.info(f"Starting debate: pro={self.pro_agent.name}, con={self.con_agent.name}")

        self._log(f"Debate: {question}")
        self._log(f"  PRO: {self.pro_agent.name}")
        self._log(f"  CON: {self.con_agent.name}")
        self._log(f"  Judge: {self.judge.name}")

        # Round 1: Opening arguments (parallel)
        self._log("\nRound 1: Opening Arguments")

        round_start = time.time()
        pro_task = self._get_opening_argument(self.pro_agent, question, "pro")
        con_task = self._get_opening_argument(self.con_agent, question, "con")

        pro_arg, con_arg = await asyncio.gather(pro_task, con_task)
        self.arguments.extend([pro_arg, con_arg])

        round_time = format_elapsed(round_start)
        self._log(f"  Round 1 complete ({round_time})")
        self._log(f"    PRO ({pro_arg.confidence:.0%}): {len(pro_arg.key_points)} key points")
        self._log(f"    CON ({con_arg.confidence:.0%}): {len(con_arg.key_points)} key points")

        # Subsequent rounds: Rebuttals
        for round_num in range(2, self.max_rounds + 1):
            self._log(f"\nRound {round_num}: Rebuttals")
            round_start = time.time()

            # Pro rebuts con's last argument
            con_last = self._get_last_argument("con")
            pro_arg = await self._get_rebuttal(self.pro_agent, question, "pro", con_last)
            self.arguments.append(pro_arg)

            # Con rebuts pro's rebuttal
            con_arg = await self._get_rebuttal(self.con_agent, question, "con", pro_arg)
            self.arguments.append(con_arg)

            round_time = format_elapsed(round_start)
            self._log(f"  Round {round_num} complete ({round_time})")
            self._log(f"    PRO ({pro_arg.confidence:.0%}): {len(pro_arg.key_points)} key points")
            self._log(f"    CON ({con_arg.confidence:.0%}): {len(con_arg.key_points)} key points")

        # Final: Judge evaluates
        self._log(f"\nJudgment: {self.judge.name} evaluating")

        judge_start = time.time()
        judgment = await self._get_judgment(question)

        judge_time = format_elapsed(judge_start)
        total_time = format_elapsed(start_time)

        self._log(f"  Judgment complete ({judge_time})")
        self._log(f"\nResult:")
        self._log(f"  Winner: {judgment.winner.upper()} ({self.pro_agent.name if judgment.winner == 'pro' else self.con_agent.name})")
        self._log(f"  Scores: PRO {judgment.score_pro:.0%} | CON {judgment.score_con:.0%}")
        self._log(f"  Total time: {total_time}")

        return DebateResult(
            question=question,
            pro_agent=self.pro_agent.name,
            con_agent=self.con_agent.name,
            arguments=self.arguments,
            judgment=judgment,
            rounds=self.max_rounds,
        )

    async def _get_opening_argument(
        self, agent: AgentBackend, question: str, position: str
    ) -> DebateArgument:
        """Get opening argument from an agent."""
        position_desc = (
            "Argue IN FAVOR of this proposal/question"
            if position == "pro"
            else "Argue AGAINST this proposal/question"
        )

        prompt = OPENING_ARGUMENT_PROMPT.format(
            question=question,
            position=position.upper(),
            position_description=position_desc,
        )

        response = await agent.invoke(prompt, role=AgentRole.COUNCIL_MEMBER)

        if response.is_error:
            return DebateArgument(
                agent_id=agent.name,
                position=position,
                round_num=1,
                argument=f"[Error: {response.error_message}]",
                key_points=[],
                confidence=0.0,
            )

        parsed = self._parse_json(response.content)
        return DebateArgument(
            agent_id=agent.name,
            position=position,
            round_num=1,
            argument=parsed.get("argument", response.content),
            key_points=parsed.get("key_points", []),
            confidence=parsed.get("confidence", 0.7),
        )

    async def _get_rebuttal(
        self,
        agent: AgentBackend,
        question: str,
        position: str,
        opponent_arg: DebateArgument,
    ) -> DebateArgument:
        """Get rebuttal from an agent."""
        position_desc = (
            "Argue IN FAVOR of this proposal/question"
            if position == "pro"
            else "Argue AGAINST this proposal/question"
        )

        prompt = REBUTTAL_PROMPT.format(
            question=question,
            position=position.upper(),
            position_description=position_desc,
            opponent_argument=opponent_arg.argument,
        )

        response = await agent.invoke(prompt, role=AgentRole.COUNCIL_MEMBER)

        current_round = max((a.round_num for a in self.arguments), default=0) + 1

        if response.is_error:
            return DebateArgument(
                agent_id=agent.name,
                position=position,
                round_num=current_round,
                argument=f"[Error: {response.error_message}]",
                key_points=[],
                confidence=0.0,
            )

        parsed = self._parse_json(response.content)
        return DebateArgument(
            agent_id=agent.name,
            position=position,
            round_num=current_round,
            argument=parsed.get("argument", response.content),
            key_points=parsed.get("key_points", []),
            confidence=parsed.get("confidence", 0.7),
        )

    async def _get_judgment(self, question: str) -> DebateJudgment:
        """Get judgment from the judge agent."""
        pro_args = "\n\n".join(
            f"Round {a.round_num}:\n{a.argument}"
            for a in self.arguments
            if a.position == "pro"
        )
        con_args = "\n\n".join(
            f"Round {a.round_num}:\n{a.argument}"
            for a in self.arguments
            if a.position == "con"
        )

        prompt = JUDGE_PROMPT.format(
            question=question,
            pro_arguments=pro_args,
            con_arguments=con_args,
        )

        response = await self.judge.invoke(prompt, role=AgentRole.ARBITER)

        if response.is_error:
            return DebateJudgment(
                judge_id=self.judge.name,
                winner="pro",
                reasoning=f"[Error: {response.error_message}]",
                score_pro=0.5,
                score_con=0.5,
                key_factors=[],
            )

        parsed = self._parse_json(response.content)
        return DebateJudgment(
            judge_id=self.judge.name,
            winner=parsed.get("winner", "pro"),
            reasoning=parsed.get("reasoning", response.content),
            score_pro=parsed.get("score_pro", 0.5),
            score_con=parsed.get("score_con", 0.5),
            key_factors=parsed.get("key_factors", []),
        )

    def _get_last_argument(self, position: str) -> DebateArgument:
        """Get the last argument for a position."""
        for arg in reversed(self.arguments):
            if arg.position == position:
                return arg
        raise ValueError(f"No arguments found for position: {position}")

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from content, with fallback."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            if start != -1:
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
                                pass
                            break
            return {}
