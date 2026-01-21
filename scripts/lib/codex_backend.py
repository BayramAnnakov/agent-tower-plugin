"""OpenAI Codex CLI backend."""

import asyncio
import json
import logging
import sys
from typing import Optional, Callable

from base import AgentBackend, StatusCallback
from response import AgentResponse, AgentRole

logger = logging.getLogger(__name__)


class CodexBackend(AgentBackend):
    """Backend for OpenAI Codex CLI.

    Uses `codex` command for non-interactive runs.
    Safe subprocess via asyncio.create_subprocess_exec (no shell).
    """

    name = "codex"

    def __init__(
        self,
        timeout: int = 300,
        model: Optional[str] = None,
        full_disk_read: bool = True,
        verbose: bool = False,
    ):
        """Initialize Codex backend.

        Args:
            timeout: Timeout in seconds
            model: Optional model override
            full_disk_read: Allow reading files outside workspace
            verbose: Whether to print status to stderr
        """
        self.timeout = timeout
        self.model = model
        self.full_disk_read = full_disk_read
        self.verbose = verbose

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke Codex CLI with the given prompt."""
        # Build command using list form (safe from injection)
        cmd = [
            "codex",
            "exec",
            "--full-auto",
            "--json",
            "--skip-git-repo-check",
        ]

        if self.full_disk_read:
            cmd.extend(["-c", 'sandbox_permissions=["disk-full-read-access"]'])

        if self.model:
            cmd.extend(["--model", self.model])

        cmd.append("-")

        logger.debug(f"Codex command: {' '.join(cmd)}")

        try:
            # Safe subprocess execution - uses exec variant, not shell
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if status_callback:
                assert proc.stdin is not None
                assert proc.stdout is not None

                proc.stdin.write(prompt.encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()
                await proc.stdin.wait_closed()

                output_lines = []
                while True:
                    try:
                        line = await asyncio.wait_for(
                            proc.stdout.readline(),
                            timeout=self.timeout,
                        )
                    except asyncio.TimeoutError:
                        break

                    if not line:
                        break

                    line_str = line.decode("utf-8").strip()
                    output_lines.append(line_str)

                    if line_str:
                        status = self._extract_status(line_str)
                        if status:
                            status_callback(self.name, status)
                            if self.verbose:
                                print(f"[{self.name}] {status}", file=sys.stderr)

                await proc.wait()
                output = "\n".join(output_lines)
                stderr_text = ""
                if proc.stderr:
                    stderr_bytes = await proc.stderr.read()
                    stderr_text = stderr_bytes.decode("utf-8") if stderr_bytes else ""

            else:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=prompt.encode("utf-8")),
                    timeout=self.timeout,
                )
                output = stdout.decode("utf-8")
                stderr_text = stderr.decode("utf-8") if stderr else ""

            content = self._parse_response(output)

            if not content.strip():
                return AgentResponse(
                    agent_id=self.name,
                    role=role,
                    content="[Error: Empty response from Codex]",
                    raw_output=output,
                    metadata={
                        "return_code": proc.returncode,
                        "stderr": stderr_text,
                        "error": "empty_response",
                    },
                )

            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=content,
                raw_output=output,
                metadata={
                    "return_code": proc.returncode,
                    "stderr": stderr_text,
                },
            )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content="[Error: Timeout]",
                metadata={"error": "timeout", "timeout_seconds": self.timeout},
            )
        except FileNotFoundError:
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content="[Error: Codex CLI not found]",
                metadata={"error": "cli_not_found"},
            )
        except Exception as e:
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=f"[Error: {str(e)}]",
                metadata={"error": str(e)},
            )

    def _extract_status(self, line: str) -> Optional[str]:
        """Extract human-readable status from a JSONL line."""
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                return None

            event_type = event.get("type", "")

            if event_type == "item.completed":
                item = event.get("item", {})
                item_type = item.get("type", "")

                if item_type == "reasoning":
                    text = item.get("text", "")
                    if text:
                        first_line = text.split("\n")[0].strip("*# ")
                        if len(first_line) > 40:
                            first_line = first_line[:37] + "..."
                        return f"Thinking: {first_line}"

                elif item_type == "tool_call":
                    tool = item.get("tool", "")
                    if tool:
                        return f"Using {tool}"

                elif item_type == "agent_message":
                    return "Writing response..."

            elif event_type == "turn.started":
                return "Starting analysis..."

            elif event_type == "turn.completed":
                return "Complete"

        except json.JSONDecodeError:
            pass

        return None

    def _parse_response(self, output: str) -> str:
        """Parse Codex JSONL output to extract the final assistant message."""
        if not output.strip():
            return ""

        lines = output.strip().split("\n")
        content_parts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)

                if not isinstance(event, dict):
                    continue

                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        text = item.get("text", "")
                        if text.strip():
                            content_parts.append(text)

            except json.JSONDecodeError:
                continue

        if content_parts:
            return "\n".join(content_parts)

        return ""

    async def health_check(self) -> bool:
        """Check if Codex CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "codex", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
        except Exception:
            return False
