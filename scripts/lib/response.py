"""Agent response models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Role of an agent in a deliberation session."""

    PRODUCER = "producer"
    REVIEWER = "reviewer"
    COUNCIL_MEMBER = "council_member"
    CHAIRMAN = "chairman"
    ARBITER = "arbiter"


class AgentResponse(BaseModel):
    """Response from an agent invocation."""

    agent_id: str = Field(description="Identifier of the agent (e.g., 'claude', 'codex')")
    role: AgentRole = Field(description="Role the agent played")
    content: str = Field(description="Main response content")
    raw_output: Optional[str] = Field(default=None, description="Raw output from subprocess")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    @property
    def is_error(self) -> bool:
        """Check if response indicates an error."""
        return self.metadata.get("error") is not None

    @property
    def error_message(self) -> Optional[str]:
        """Get error message if present."""
        return self.metadata.get("error")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata,
            "is_error": self.is_error,
        }
