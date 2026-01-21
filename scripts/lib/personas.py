"""Dynamic persona assignment for council members.

Analyzes tasks and assigns complementary expert roles to agents.
"""

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Persona:
    """A persona/role for a council member."""

    name: str
    focus_areas: list[str]
    system_prompt: str

    def format_prompt(self, base_prompt: str) -> str:
        """Wrap base prompt with persona context."""
        return f"""You are acting as a {self.name}.

FOCUS AREAS: {', '.join(self.focus_areas)}

{self.system_prompt}

---

{base_prompt}"""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


# Predefined personas for common analysis types
SECURITY_ANALYST = Persona(
    name="Security Analyst",
    focus_areas=["authentication", "authorization", "injection vulnerabilities", "data exposure", "cryptography"],
    system_prompt="""Analyze from a security perspective:
- Look for OWASP Top 10 vulnerabilities
- Check authentication and authorization flows
- Identify potential injection points (SQL, command, XSS)
- Review data handling and exposure risks
- Assess cryptographic implementations"""
)

SYSTEMS_ARCHITECT = Persona(
    name="Systems Architect",
    focus_areas=["scalability", "performance", "load handling", "caching", "infrastructure"],
    system_prompt="""Analyze from an architectural perspective:
- Evaluate scalability and load handling
- Identify performance bottlenecks
- Review caching strategies
- Assess infrastructure and deployment patterns
- Consider failure modes and resilience"""
)

CODE_QUALITY_REVIEWER = Persona(
    name="Code Quality Reviewer",
    focus_areas=["maintainability", "readability", "patterns", "testing", "documentation"],
    system_prompt="""Analyze from a code quality perspective:
- Evaluate code organization and structure
- Check for proper abstraction and DRY principles
- Review error handling patterns
- Assess test coverage and testability
- Look for code smells and anti-patterns"""
)

BUSINESS_STRATEGIST = Persona(
    name="Business Strategist",
    focus_areas=["market fit", "competitive advantage", "monetization", "growth", "risks"],
    system_prompt="""Analyze from a business strategy perspective:
- Evaluate market opportunity and timing
- Assess competitive landscape
- Review monetization potential
- Identify growth levers and channels
- Consider business model risks"""
)

PRODUCT_MANAGER = Persona(
    name="Product Manager",
    focus_areas=["user needs", "feature prioritization", "UX", "roadmap", "metrics"],
    system_prompt="""Analyze from a product management perspective:
- Evaluate user needs and pain points
- Assess feature prioritization
- Review user experience implications
- Consider product roadmap impact
- Identify key metrics for success"""
)

DEVIL_ADVOCATE = Persona(
    name="Devil's Advocate",
    focus_areas=["risks", "failure modes", "edge cases", "assumptions", "counterarguments"],
    system_prompt="""Challenge assumptions and find weaknesses:
- Question underlying assumptions
- Identify potential failure modes
- Find edge cases and corner scenarios
- Present counterarguments
- Highlight overlooked risks"""
)

DATA_ENGINEER = Persona(
    name="Data Engineer",
    focus_areas=["data modeling", "pipelines", "storage", "queries", "data quality"],
    system_prompt="""Analyze from a data engineering perspective:
- Evaluate data model design
- Review data pipeline architecture
- Assess storage and retrieval patterns
- Check query performance implications
- Consider data quality and consistency"""
)

DEVOPS_ENGINEER = Persona(
    name="DevOps Engineer",
    focus_areas=["deployment", "monitoring", "CI/CD", "infrastructure", "reliability"],
    system_prompt="""Analyze from a DevOps perspective:
- Evaluate deployment strategies
- Review monitoring and observability
- Assess CI/CD implications
- Check infrastructure requirements
- Consider operational reliability"""
)

UX_DESIGNER = Persona(
    name="UX Designer",
    focus_areas=["usability", "accessibility", "user flows", "interaction design", "visual hierarchy"],
    system_prompt="""Analyze from a UX design perspective:
- Evaluate usability and learnability
- Check accessibility compliance
- Review user flows and navigation
- Assess interaction patterns
- Consider visual hierarchy and clarity"""
)

FINANCIAL_ANALYST = Persona(
    name="Financial Analyst",
    focus_areas=["unit economics", "pricing", "margins", "projections", "funding"],
    system_prompt="""Analyze from a financial perspective:
- Evaluate unit economics
- Review pricing strategy
- Assess cost structure and margins
- Consider financial projections
- Identify funding requirements"""
)

# Keywords to persona mapping
TASK_KEYWORDS = {
    # Security-related
    ("security", "auth", "authentication", "authorization", "vulnerability", "owasp",
     "injection", "xss", "csrf", "encryption", "credentials", "password", "token"): SECURITY_ANALYST,

    # Architecture/Performance
    ("scalability", "performance", "architecture", "scale", "load", "throughput",
     "latency", "caching", "distributed", "microservice", "infrastructure"): SYSTEMS_ARCHITECT,

    # Code quality
    ("refactor", "code review", "maintainability", "testing", "test coverage",
     "code quality", "clean code", "patterns", "best practices"): CODE_QUALITY_REVIEWER,

    # Business/Strategy
    ("business", "strategy", "market", "competitive", "monetization", "revenue",
     "startup", "idea", "opportunity", "growth", "traction"): BUSINESS_STRATEGIST,

    # Product
    ("product", "feature", "user", "ux", "roadmap", "prioritize", "requirements",
     "user story", "customer", "feedback"): PRODUCT_MANAGER,

    # Data
    ("database", "data model", "schema", "query", "sql", "nosql", "pipeline",
     "etl", "data warehouse", "analytics"): DATA_ENGINEER,

    # DevOps
    ("deploy", "deployment", "ci/cd", "kubernetes", "docker", "monitoring",
     "observability", "infrastructure", "ops", "reliability"): DEVOPS_ENGINEER,

    # UX/Design
    ("ui", "interface", "design", "usability", "accessibility", "a11y",
     "navigation", "layout", "visual"): UX_DESIGNER,

    # Financial
    ("pricing", "cost", "budget", "revenue", "profit", "margin", "unit economics",
     "funding", "investment", "financial"): FINANCIAL_ANALYST,
}


def _score_persona(task: str, keywords: tuple[str, ...]) -> int:
    """Score how well a persona matches a task based on keyword matches."""
    task_lower = task.lower()
    score = 0
    for keyword in keywords:
        if keyword in task_lower:
            score += 1
            # Bonus for exact word match
            if re.search(rf'\b{re.escape(keyword)}\b', task_lower):
                score += 1
    return score


def infer_personas(task: str, num_agents: int) -> list[Persona]:
    """Infer appropriate personas for a task.

    Args:
        task: The task description
        num_agents: Number of agents to assign personas to

    Returns:
        List of personas, one for each agent
    """
    # Score all personas
    scored_personas: list[tuple[int, Persona]] = []
    for keywords, persona in TASK_KEYWORDS.items():
        score = _score_persona(task, keywords)
        if score > 0:
            scored_personas.append((score, persona))

    # Sort by score descending
    scored_personas.sort(key=lambda x: x[0], reverse=True)

    # Get unique personas (remove duplicates)
    selected: list[Persona] = []
    seen_names: set[str] = set()

    for _, persona in scored_personas:
        if persona.name not in seen_names:
            selected.append(persona)
            seen_names.add(persona.name)
            if len(selected) >= num_agents:
                break

    # If we don't have enough, add complementary defaults
    defaults = [
        CODE_QUALITY_REVIEWER,
        DEVIL_ADVOCATE,
        SYSTEMS_ARCHITECT,
        BUSINESS_STRATEGIST,
    ]

    for persona in defaults:
        if len(selected) >= num_agents:
            break
        if persona.name not in seen_names:
            selected.append(persona)
            seen_names.add(persona.name)

    # Always include Devil's Advocate if we have 3+ agents
    if num_agents >= 3 and DEVIL_ADVOCATE.name not in seen_names:
        # Replace the last one with Devil's Advocate
        if len(selected) >= num_agents:
            selected[-1] = DEVIL_ADVOCATE
        else:
            selected.append(DEVIL_ADVOCATE)

    return selected[:num_agents]


def get_persona_for_task(task: str, agent_index: int, total_agents: int) -> Optional[Persona]:
    """Get persona for a specific agent given a task.

    Args:
        task: The task description
        agent_index: Index of this agent (0-based)
        total_agents: Total number of agents

    Returns:
        Persona for this agent, or None if no special persona
    """
    personas = infer_personas(task, total_agents)
    if agent_index < len(personas):
        return personas[agent_index]
    return None


def format_persona_assignment(personas: list[Persona], agent_names: list[str]) -> str:
    """Format persona assignments for display.

    Args:
        personas: List of assigned personas
        agent_names: List of agent names

    Returns:
        Formatted string for display
    """
    lines = ["Assigning perspectives:"]
    for name, persona in zip(agent_names, personas):
        focus = ", ".join(persona.focus_areas[:3])
        lines.append(f"  {name} -> {persona.name} (focus: {focus})")
    return "\n".join(lines)
