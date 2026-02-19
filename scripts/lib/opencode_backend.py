"""OpenCode CLI backend."""

import asyncio
import json
import logging
from typing import Optional

from base import AgentBackend, StatusCallback
from response import AgentResponse, AgentRole

logger = logging.getLogger(__name__)


class OpencodeBackend(AgentBackend):
    """Backend for OpenCode CLI.

    Wraps `opencode run` command for non-interactive AI invocation.
    Supports any model available through opencode (GitHub Copilot, etc.).
    """

    name = "opencode"

    def __init__(
        self,
        model: str = "github-copilot/gemini-3-pro-preview",
        timeout: int = 600,
        verbose: bool = False,
    ):
        """Initialize OpenCode backend.

        Args:
            model: Full model ID (e.g., 'github-copilot/gemini-3-pro-preview')
            timeout: Timeout in seconds
            verbose: Whether to print status to stderr
        """
        self.model = model
        self.timeout = timeout
        self.verbose = verbose
        # Short name for display (e.g., "gemini-3-pro-preview")
        self.agent_id = model.split("/")[-1] if "/" in model else model

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke opencode CLI with the given prompt."""
        raise NotImplementedError("invoke not yet implemented")

    async def health_check(self) -> bool:
        """Check if opencode CLI is available."""
        raise NotImplementedError("health_check not yet implemented")
