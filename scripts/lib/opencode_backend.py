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

    def _parse_jsonl_response(self, output: str) -> str:
        """Parse JSONL output from opencode CLI.

        Extracts text from 'type: text' events and concatenates them.

        Args:
            output: Raw JSONL output from opencode run

        Returns:
            Concatenated text content
        """
        if not output.strip():
            return ""

        content_parts = []

        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    continue

                # Extract text from type: "text" events
                if event.get("type") == "text":
                    part = event.get("part", {})
                    if isinstance(part, dict) and "text" in part:
                        content_parts.append(part["text"])

            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue

        return "".join(content_parts)

    def _build_command(self, prompt: str) -> list[str]:
        """Build the opencode command.

        Args:
            prompt: The prompt to send

        Returns:
            Command as list of strings (safe for subprocess)
        """
        return [
            "opencode", "run",
            prompt,
            "-m", self.model,
            "--format", "json",
        ]

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke opencode CLI with the given prompt.

        Args:
            prompt: The prompt/task to send
            context: Optional context dictionary (unused for now)
            role: The role this agent is playing
            status_callback: Optional callback for status updates

        Returns:
            AgentResponse with the agent's output
        """
        cmd = self._build_command(prompt)

        logger.debug(f"OpenCode command: {cmd[0]} {cmd[1]} ... -m {self.model}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout,
            )

            output = stdout.decode("utf-8")
            content = self._parse_jsonl_response(output)

            return AgentResponse(
                agent_id=self.agent_id,
                role=role,
                content=content,
                raw_output=output,
                metadata={
                    "model": self.model,
                    "return_code": proc.returncode,
                },
            )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent_id=self.agent_id,
                role=role,
                content="[Error: Timeout]",
                metadata={"error": "timeout", "timeout_seconds": self.timeout},
            )
        except FileNotFoundError:
            return AgentResponse(
                agent_id=self.agent_id,
                role=role,
                content="[Error: OpenCode CLI not found]",
                metadata={"error": "cli_not_found"},
            )
        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                role=role,
                content=f"[Error: {str(e)}]",
                metadata={"error": str(e)},
            )

    async def health_check(self) -> bool:
        """Check if opencode CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "opencode", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
        except Exception:
            return False
