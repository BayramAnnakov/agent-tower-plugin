"""Claude Code CLI backend."""

import asyncio
import json
import logging
import os
import sys
from typing import Optional, Callable

from base import AgentBackend, StatusCallback
from response import AgentResponse, AgentRole

logger = logging.getLogger(__name__)


class ClaudeBackend(AgentBackend):
    """Backend for Claude Code CLI.

    Uses `claude -p` (print mode) to invoke Claude non-interactively.
    Safe subprocess execution via asyncio.create_subprocess_exec (no shell).
    """

    name = "claude"

    def __init__(
        self,
        model: str = "opus",
        max_turns: int = 25,
        timeout: int = 600,
        allowed_tools: Optional[list[str]] = None,
        verbose: bool = False,
    ):
        """Initialize Claude backend.

        Args:
            model: Model to use (opus, sonnet, haiku, default)
            max_turns: Maximum agentic turns (default 25 for thorough analysis)
            timeout: Timeout in seconds (default 10 min for complex tasks)
            allowed_tools: List of allowed tools
            verbose: Whether to print status to stderr
        """
        self.model = model
        self.max_turns = max_turns
        self.timeout = timeout
        self.allowed_tools = allowed_tools or [
            "Read", "Grep", "Glob", "Bash", "Task"
        ]
        self.verbose = verbose

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke Claude Code CLI with the given prompt."""
        # Use stream-json for real-time status updates
        output_format = "stream-json" if status_callback else "json"

        cmd = [
            "claude",
            "-p",
            "--output-format", output_format,
            "--model", self.model,
            "--max-turns", str(self.max_turns),
            "--allowedTools", ",".join(self.allowed_tools),
        ]

        # stream-json requires --verbose in print mode
        if status_callback:
            cmd.append("--verbose")

        logger.debug(f"Claude command: {' '.join(cmd)}")

        # Create clean environment without CLAUDECODE to allow nested invocation
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            if status_callback:
                assert proc.stdin is not None
                assert proc.stdout is not None

                proc.stdin.write(prompt.encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()
                await proc.stdin.wait_closed()

                output_lines = []
                content_parts = []

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
                    if not line_str:
                        continue

                    output_lines.append(line_str)
                    status, content = self._parse_stream_event(line_str)
                    if status:
                        status_callback(self.name, status)
                        if self.verbose:
                            print(f"[{self.name}] {status}", file=sys.stderr)
                    if content:
                        content_parts.append(content)

                await proc.wait()
                output = "\n".join(output_lines)
                final_content = "\n".join(content_parts) if content_parts else self._parse_response(output)

            else:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=prompt.encode("utf-8")),
                    timeout=self.timeout,
                )
                output = stdout.decode("utf-8")
                final_content = self._parse_response(output)

            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=final_content,
                raw_output=output,
                metadata={
                    "model": self.model,
                    "return_code": proc.returncode,
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
                content="[Error: Claude CLI not found]",
                metadata={"error": "cli_not_found"},
            )
        except Exception as e:
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=f"[Error: {str(e)}]",
                metadata={"error": str(e)},
            )

    def _parse_stream_event(self, line: str) -> tuple[Optional[str], Optional[str]]:
        """Parse a streaming JSON event for status and content."""
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                return None, None

            event_type = event.get("type", "")

            if event_type == "assistant/tool_use":
                tool = event.get("tool", {})
                tool_name = tool.get("name", "")
                if tool_name:
                    tool_input = tool.get("input", {})
                    if "file_path" in tool_input:
                        path = tool_input["file_path"]
                        if len(path) > 30:
                            path = "..." + path[-27:]
                        return f"Reading: {path}", None
                    elif "pattern" in tool_input:
                        return f"Searching: {tool_input['pattern'][:20]}", None
                    elif "command" in tool_input:
                        return f"Running: {tool_input['command'][:25]}", None
                    else:
                        return f"Using {tool_name}", None

            elif event_type == "assistant/text":
                text = event.get("text", "")
                if text:
                    return "Writing response...", text

            elif event_type == "result":
                return "Complete", event.get("result", "")

            elif event_type == "message":
                role = event.get("role", "")
                if role == "assistant":
                    return "Thinking...", None

        except json.JSONDecodeError:
            pass

        return None, None

    def _parse_response(self, output: str) -> str:
        """Parse Claude CLI JSON output to extract content."""
        if not output.strip():
            return ""

        try:
            data = json.loads(output)
            if isinstance(data, dict):
                if "result" in data:
                    return str(data["result"])
                if "content" in data:
                    return str(data["content"])
                if "message" in data:
                    msg = data["message"]
                    if isinstance(msg, dict) and "content" in msg:
                        return str(msg["content"])
                    return str(msg)
            return str(data)

        except json.JSONDecodeError:
            return self._extract_text_from_output(output)

    def _extract_text_from_output(self, output: str) -> str:
        """Extract text when JSON parsing fails."""
        start = output.find("{")
        if start != -1:
            depth = 0
            for i, char in enumerate(output[start:], start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(output[start : i + 1])
                            if isinstance(data, dict) and "result" in data:
                                return str(data["result"])
                        except json.JSONDecodeError:
                            pass
                        break
        return output.strip()

    async def health_check(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
        except Exception:
            return False
