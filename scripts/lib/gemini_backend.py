"""Google Gemini CLI backend."""

import asyncio
import json
import logging
import sys
from typing import Optional, Callable

from base import AgentBackend, StatusCallback
from response import AgentResponse, AgentRole

logger = logging.getLogger(__name__)


class GeminiBackend(AgentBackend):
    """Backend for Google Gemini CLI.

    Uses `gemini` command with JSON output for non-interactive runs.
    Safe subprocess via asyncio.create_subprocess_exec (no shell).
    """

    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-3-pro-preview",
        timeout: int = 600,
        sandbox: bool = True,
        verbose: bool = False,
    ):
        """Initialize Gemini backend.

        Args:
            model: Model to use (default: gemini-3-pro-preview)
            timeout: Timeout in seconds
            sandbox: Whether to run in sandbox mode
            verbose: Whether to print status to stderr
        """
        self.model = model
        self.timeout = timeout
        self.sandbox = sandbox
        self.verbose = verbose

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke Gemini CLI with the given prompt."""
        output_format = "stream-json" if status_callback else "json"

        # Build command as list (safe from injection)
        cmd = [
            "gemini",
            "-o", output_format,
            "-y",  # YOLO mode
        ]

        if self.model:
            cmd.extend(["-m", self.model])

        if self.sandbox:
            cmd.append("-s")

        cmd.append(prompt)

        logger.debug(f"Gemini command: {' '.join(cmd[:6])}...")

        try:
            # Safe subprocess - uses exec variant, not shell
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if status_callback:
                assert proc.stdout is not None

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
                    proc.communicate(),
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
                content="[Error: Gemini CLI not found]",
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

            if event_type == "tool_use" or "tool" in event:
                tool_name = event.get("tool", {}).get("name", "") or event.get("name", "")
                if tool_name:
                    return f"Using {tool_name}", None

            if event_type == "text" or "text" in event:
                text = event.get("text", "")
                if text:
                    return "Writing response...", text

            if event_type == "result" or "result" in event:
                return "Complete", event.get("result", "")

            if event_type == "message_start":
                return "Thinking...", None

            if event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    return None, delta.get("text", "")

        except json.JSONDecodeError:
            pass

        return None, None

    def _parse_response(self, output: str) -> str:
        """Parse Gemini CLI JSON output to extract content."""
        if not output.strip():
            return ""

        try:
            data = json.loads(output)
            if isinstance(data, dict):
                for key in ["result", "content", "text", "message", "response"]:
                    if key in data:
                        value = data[key]
                        if isinstance(value, str):
                            return value
                        if isinstance(value, dict) and "text" in value:
                            return str(value["text"])
                        if isinstance(value, dict) and "content" in value:
                            return str(value["content"])
                return str(data)
            return str(data)
        except json.JSONDecodeError:
            pass

        # Try JSONL format
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

                if "text" in event:
                    content_parts.append(event["text"])
                elif "content" in event:
                    content_parts.append(str(event["content"]))
                elif "result" in event:
                    content_parts.append(str(event["result"]))
                elif event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("text"):
                        content_parts.append(delta["text"])

            except json.JSONDecodeError:
                continue

        if content_parts:
            return "".join(content_parts)

        return output.strip()

    async def health_check(self) -> bool:
        """Check if Gemini CLI is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gemini", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
        except Exception:
            return False
