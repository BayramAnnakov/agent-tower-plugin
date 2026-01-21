"""Base agent backend interface."""

from abc import ABC, abstractmethod
from typing import Optional, Callable

from response import AgentResponse, AgentRole

# Type for status callback: (agent_name, status_text) -> None
StatusCallback = Callable[[str, str], None]


class AgentBackend(ABC):
    """Abstract base class for agent backends.

    Each backend wraps a specific AI agent CLI (e.g., Claude Code, Codex)
    and provides a unified interface for invoking the agent.
    """

    name: str = "base"

    @abstractmethod
    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Execute a prompt and return the agent's response.

        Args:
            prompt: The prompt/task to send to the agent
            context: Optional context dictionary (e.g., previous responses)
            role: The role this agent is playing in the session
            status_callback: Optional callback for real-time status updates

        Returns:
            AgentResponse with the agent's output
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the agent is available and working.

        Returns:
            True if the agent is available, False otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
