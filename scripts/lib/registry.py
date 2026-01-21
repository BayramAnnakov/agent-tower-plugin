"""Agent registry for discovery and instantiation."""

from typing import Optional

from base import AgentBackend
from claude_backend import ClaudeBackend
from codex_backend import CodexBackend
from gemini_backend import GeminiBackend


# Registry of available agent backends
AGENTS: dict[str, type[AgentBackend]] = {
    "claude": ClaudeBackend,
    "codex": CodexBackend,
    "gemini": GeminiBackend,
}


def get_agent(name: str, **kwargs) -> AgentBackend:
    """Get an agent backend by name.

    Args:
        name: Agent name (e.g., "claude", "codex")
        **kwargs: Additional arguments passed to the backend constructor

    Returns:
        Instantiated agent backend

    Raises:
        ValueError: If agent name is unknown
    """
    if name not in AGENTS:
        available = ", ".join(AGENTS.keys())
        raise ValueError(f"Unknown agent: {name}. Available agents: {available}")

    return AGENTS[name](**kwargs)


async def get_available_agents() -> list[str]:
    """Get list of agents that are currently available.

    Performs health checks on all registered agents.

    Returns:
        List of agent names that passed health check
    """
    available = []

    for name, agent_class in AGENTS.items():
        try:
            agent = agent_class()
            if await agent.health_check():
                available.append(name)
        except Exception:
            # Skip agents that fail to instantiate
            pass

    return available


def register_agent(name: str, agent_class: type[AgentBackend]) -> None:
    """Register a new agent backend.

    Args:
        name: Name to register the agent under
        agent_class: Agent backend class (must inherit from AgentBackend)
    """
    if not issubclass(agent_class, AgentBackend):
        raise TypeError(f"{agent_class} must inherit from AgentBackend")

    AGENTS[name] = agent_class


def list_agents() -> list[str]:
    """List all registered agent names."""
    return list(AGENTS.keys())
