"""Council mode - parallel opinions with synthesis (no Rich UI)."""

import asyncio
import json
import logging
import sys
import time
from typing import Optional

from base import AgentBackend
from response import AgentRole
from council import CouncilOpinion, PeerRanking, CouncilSynthesis, CouncilResult
from personas import Persona, infer_personas

logger = logging.getLogger(__name__)


def format_elapsed(start_time: float) -> str:
    """Format elapsed time as MM:SS."""
    elapsed = int(time.time() - start_time)
    mins, secs = divmod(elapsed, 60)
    return f"{mins}:{secs:02d}"


OPINION_PROMPT = """You are a council member performing a thorough analysis of this task.

TASK: {task}

IMPORTANT: Do a COMPREHENSIVE analysis. If the task involves code or files:
1. Read and analyze ALL relevant files thoroughly
2. Search the codebase for related patterns
3. Check for security issues, bugs, edge cases
4. Look at error handling, input validation, authentication
5. Consider dependencies and external calls

Take your time - thoroughness is more important than speed.

Provide your independent analysis with specific findings and evidence.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "opinion": "Your full, detailed analysis with specific findings and file references",
  "confidence": 0.0-1.0,
  "key_points": ["Specific finding 1", "Specific finding 2", "Specific finding 3"]
}}
"""


RANKING_PROMPT = """Review these anonymized responses to a task and rank them.

TASK: {task}

RESPONSES:
{responses}

Evaluate each response for:
- Accuracy and correctness
- Depth of insight
- Practical usefulness
- Clarity of reasoning

Rank each response (1=best, 2=second best, etc.). Explain your reasoning.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "rankings": {{"A": 1, "B": 2, "C": 3}},
  "reasoning": {{
    "A": "Why this was ranked here",
    "B": "Why this was ranked here"
  }}
}}
"""


SYNTHESIS_PROMPT = """You are the council chairman. Synthesize these council opinions into a final answer.

TASK: {task}

COUNCIL OPINIONS:
{opinions}

PEER RANKINGS:
{rankings}

Create a comprehensive final synthesis that:
1. Captures the consensus view across all opinions
2. Weighs insights by the peer rankings (higher-ranked opinions carry more weight)
3. Notes any important dissenting perspectives
4. Provides clear, actionable conclusions

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "final_answer": "Comprehensive synthesized answer",
  "consensus_level": 0.0-1.0,
  "dissenting_views": ["Notable disagreements or alternative views"],
  "key_insights": ["Key insight 1", "Key insight 2", "Key insight 3"]
}}
"""


class CouncilMode:
    """Multi-agent council with parallel opinions and chairman synthesis.

    Stages:
    - Stage 1: All members provide independent opinions (parallel)
    - Stage 2: Each member reviews and ranks others' opinions (anonymized)
    - Stage 3: Chairman synthesizes all opinions weighted by rankings
    """

    def __init__(
        self,
        members: list[AgentBackend],
        chairman: Optional[AgentBackend] = None,
        use_personas: bool = True,
        verbose: bool = False,
        max_concurrent: int = 5,
    ):
        """Initialize council mode.

        Args:
            members: List of agent backends to serve as council members
            chairman: Agent to synthesize final answer (defaults to first member)
            use_personas: Whether to dynamically assign personas based on task
            verbose: Whether to print progress to stderr
            max_concurrent: Maximum concurrent agent invocations (default: 5)
        """
        if len(members) < 2:
            raise ValueError("Council requires at least 2 members")

        self.members = members
        self.chairman = chairman or members[0]
        self.use_personas = use_personas
        self.verbose = verbose
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.opinions: dict[str, CouncilOpinion] = {}
        self.rankings: list[PeerRanking] = []
        self.personas: dict[str, Persona] = {}

    def _log(self, msg: str):
        """Log message to stderr if verbose."""
        if self.verbose:
            print(msg, file=sys.stderr)

    async def run(self, task: str) -> CouncilResult:
        """Run council deliberation.

        Args:
            task: Free-form task/question for the council

        Returns:
            CouncilResult with opinions, rankings, and synthesis
        """
        start_time = time.time()
        member_names = [m.name for m in self.members]
        logger.info(f"Starting council deliberation with members: {member_names}")

        # Infer personas based on task
        personas_assigned = []
        if self.use_personas:
            personas = infer_personas(task, len(self.members))
            for member, persona in zip(self.members, personas):
                self.personas[member.name] = persona
                personas_assigned.append({
                    "agent": member.name,
                    "persona": persona.name,
                    "focus_areas": persona.focus_areas[:3],
                })
            self._log(f"Assigned personas: {personas_assigned}")

        # Stage 1: Parallel first opinions (with concurrency limit)
        self._log(f"Stage 1: Gathering opinions from {len(self.members)} council members (max {self.max_concurrent} concurrent)")

        async def get_opinion_with_timing(member):
            async with self._semaphore:  # Limit concurrent subprocess invocations
                agent_start = time.time()
                result = await self._get_opinion(member, task)
                elapsed = format_elapsed(agent_start)
                self._log(f"  {member.name}: completed in {elapsed}")
                return result

        opinions = await asyncio.gather(*[get_opinion_with_timing(m) for m in self.members])

        for member, opinion in zip(self.members, opinions):
            self.opinions[member.name] = opinion

        stage1_time = format_elapsed(start_time)
        self._log(f"Stage 1 complete in {stage1_time}")

        # Stage 2: Cross-review and ranking
        self._log("Stage 2: Cross-review and ranking")

        stage2_start = time.time()
        anon_map = self._create_anonymized_map()
        anon_responses = self._format_anonymized_responses(anon_map)

        async def get_ranking_with_timing(member):
            async with self._semaphore:  # Limit concurrent subprocess invocations
                agent_start = time.time()
                result = await self._get_ranking(member, task, anon_responses)
                elapsed = format_elapsed(agent_start)
                self._log(f"  {member.name}: ranked in {elapsed}")
                return result

        rankings = await asyncio.gather(*[get_ranking_with_timing(m) for m in self.members])

        reverse_anon_map = {v: k for k, v in anon_map.items()}
        self.rankings = [
            self._deanonymize_ranking(ranking, reverse_anon_map)
            for ranking in rankings
        ]

        stage2_time = format_elapsed(stage2_start)
        self._log(f"Stage 2 complete in {stage2_time}")

        # Stage 3: Chairman synthesis
        self._log(f"Stage 3: Chairman ({self.chairman.name}) synthesizing")

        stage3_start = time.time()
        synthesis = await self._synthesize(task)

        stage3_time = format_elapsed(stage3_start)
        total_time = format_elapsed(start_time)

        self._log(f"Stage 3 complete in {stage3_time}")
        self._log(f"Council deliberation complete (total: {total_time})")
        self._log(f"Consensus level: {synthesis.consensus_level:.0%}")

        return CouncilResult(
            task=task,
            opinions=self.opinions,
            rankings=self.rankings,
            synthesis=synthesis,
        )

    async def _get_opinion(self, member: AgentBackend, task: str) -> CouncilOpinion:
        """Get opinion from a council member."""
        base_prompt = OPINION_PROMPT.format(task=task)

        # Apply persona if assigned
        persona = self.personas.get(member.name)
        if persona:
            prompt = persona.format_prompt(base_prompt)
        else:
            prompt = base_prompt

        response = await member.invoke(prompt, role=AgentRole.COUNCIL_MEMBER)

        if response.is_error:
            return CouncilOpinion(
                agent_id=member.name,
                opinion=f"[Error: {response.error_message}]",
                confidence=0.0,
                key_points=[],
            )

        parsed = self._parse_json(response.content)
        return CouncilOpinion(
            agent_id=member.name,
            opinion=parsed.get("opinion", response.content),
            confidence=parsed.get("confidence", 0.7),
            key_points=parsed.get("key_points", []),
        )

    async def _get_ranking(
        self, member: AgentBackend, task: str, anon_responses: str
    ) -> dict:
        """Get ranking from a council member."""
        prompt = RANKING_PROMPT.format(task=task, responses=anon_responses)
        response = await member.invoke(prompt, role=AgentRole.COUNCIL_MEMBER)

        if response.is_error:
            return {"rankings": {}, "reasoning": {}}

        return self._parse_json(response.content)

    async def _synthesize(self, task: str) -> CouncilSynthesis:
        """Synthesize all opinions into final answer."""
        opinions_text = "\n\n".join([
            f"## {name} (confidence: {op.confidence:.0%}):\n{op.opinion}"
            for name, op in self.opinions.items()
        ])

        rankings_summary = self._summarize_rankings()

        prompt = SYNTHESIS_PROMPT.format(
            task=task,
            opinions=opinions_text,
            rankings=rankings_summary,
        )

        response = await self.chairman.invoke(prompt, role=AgentRole.CHAIRMAN)

        if response.is_error:
            return CouncilSynthesis(
                chairman_id=self.chairman.name,
                final_answer=f"[Error: {response.error_message}]",
                consensus_level=0.0,
                dissenting_views=[],
                key_insights=[],
            )

        parsed = self._parse_json(response.content)
        return CouncilSynthesis(
            chairman_id=self.chairman.name,
            final_answer=parsed.get("final_answer", response.content),
            consensus_level=parsed.get("consensus_level", 0.5),
            dissenting_views=parsed.get("dissenting_views", []),
            key_insights=parsed.get("key_insights", []),
        )

    def _create_anonymized_map(self) -> dict[str, str]:
        """Create mapping from agent names to anonymized IDs (A, B, C...)."""
        return {
            member.name: chr(65 + i)
            for i, member in enumerate(self.members)
        }

    def _format_anonymized_responses(self, anon_map: dict[str, str]) -> str:
        """Format responses with anonymized IDs."""
        lines = []
        for member in self.members:
            anon_id = anon_map[member.name]
            opinion = self.opinions.get(member.name)
            if opinion:
                lines.append(f"Response {anon_id}:\n{opinion.opinion}")
        return "\n\n---\n\n".join(lines)

    def _deanonymize_ranking(
        self, ranking: dict, reverse_map: dict[str, str]
    ) -> PeerRanking:
        """Convert anonymized ranking back to real agent IDs."""
        rankings = ranking.get("rankings", {})
        reasoning = ranking.get("reasoning", {})

        real_rankings = {
            reverse_map.get(anon_id, anon_id): rank
            for anon_id, rank in rankings.items()
        }
        real_reasoning = {
            reverse_map.get(anon_id, anon_id): reason
            for anon_id, reason in reasoning.items()
        }

        return PeerRanking(
            reviewer_id="unknown",
            rankings=real_rankings,
            reasoning=real_reasoning,
        )

    def _summarize_rankings(self) -> str:
        """Summarize peer rankings for synthesis prompt."""
        scores: dict[str, list[int]] = {}
        for ranking in self.rankings:
            for agent_id, rank in ranking.rankings.items():
                if agent_id not in scores:
                    scores[agent_id] = []
                scores[agent_id].append(rank)

        if not scores:
            return "No peer rankings available."

        lines = ["Average rankings (1=best):"]
        avg_scores = [
            (agent_id, sum(ranks) / len(ranks))
            for agent_id, ranks in scores.items()
        ]
        avg_scores.sort(key=lambda x: x[1])

        for agent_id, avg in avg_scores:
            lines.append(f"  {agent_id}: {avg:.1f}")

        return "\n".join(lines)

    def _parse_json(self, content: str) -> dict:
        """Parse JSON from content, with fallback."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON
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
