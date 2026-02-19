# OpenCode Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OpenCode backend to Agent Tower, enabling access to Gemini/GPT/Claude via the `opencode` CLI for environments where direct vendor CLIs are blocked.

**Architecture:** Create `OpencodeBackend` class following the same pattern as `GeminiBackend`. Register three pre-configured agents (`opencode-gemini`, `opencode-gpt`, `opencode-claude`) using factory lambdas. TDD approach with tests first.

**Tech Stack:** Python 3.11+, asyncio, pydantic, pytest

---

## Task 1: Create OpencodeBackend Test File

**Files:**
- Create: `tests/test_opencode_backend.py`

**Step 1: Write test file scaffold and import test**

```python
#!/usr/bin/env python3
"""Tests for OpenCode backend."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))

import pytest
from opencode_backend import OpencodeBackend
from response import AgentRole


class TestOpencodeBackend:
    """Tests for OpencodeBackend class."""

    def test_backend_exists(self):
        """Test that OpencodeBackend can be imported."""
        assert OpencodeBackend is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeBackend::test_backend_exists -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'opencode_backend'`

**Step 3: Commit test scaffold**

```bash
git add tests/test_opencode_backend.py
git commit -m "test: add opencode backend test scaffold"
```

---

## Task 2: Create Minimal OpencodeBackend Class

**Files:**
- Create: `scripts/lib/opencode_backend.py`

**Step 1: Write minimal backend that passes import test**

```python
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
```

**Step 2: Run test to verify it passes**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeBackend::test_backend_exists -v`

Expected: PASS

**Step 3: Commit minimal backend**

```bash
git add scripts/lib/opencode_backend.py
git commit -m "feat: add minimal OpencodeBackend class"
```

---

## Task 3: Test and Implement Backend Initialization

**Files:**
- Modify: `tests/test_opencode_backend.py`
- Modify: `scripts/lib/opencode_backend.py` (if needed)

**Step 1: Add initialization tests**

Add to `tests/test_opencode_backend.py`:

```python
    def test_default_initialization(self):
        """Test backend initializes with defaults."""
        backend = OpencodeBackend()
        assert backend.name == "opencode"
        assert backend.model == "github-copilot/gemini-3-pro-preview"
        assert backend.timeout == 600
        assert backend.agent_id == "gemini-3-pro-preview"

    def test_custom_initialization(self):
        """Test backend initializes with custom values."""
        backend = OpencodeBackend(
            model="github-copilot/gpt-5.1-codex",
            timeout=300,
        )
        assert backend.model == "github-copilot/gpt-5.1-codex"
        assert backend.timeout == 300
        assert backend.agent_id == "gpt-5.1-codex"

    def test_agent_id_extraction(self):
        """Test agent_id is extracted from model path."""
        backend = OpencodeBackend(model="github-copilot/claude-sonnet-4.6")
        assert backend.agent_id == "claude-sonnet-4.6"

        # Model without slash uses full name
        backend2 = OpencodeBackend(model="local-model")
        assert backend2.agent_id == "local-model"
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py -v`

Expected: PASS (the minimal implementation already supports this)

**Step 3: Commit**

```bash
git add tests/test_opencode_backend.py
git commit -m "test: add opencode backend initialization tests"
```

---

## Task 4: Test and Implement Health Check

**Files:**
- Modify: `tests/test_opencode_backend.py`
- Modify: `scripts/lib/opencode_backend.py`

**Step 1: Add health check test**

Add to `tests/test_opencode_backend.py`:

```python
class TestOpencodeHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_cli_not_found(self):
        """Test health check returns False when CLI not installed."""
        backend = OpencodeBackend()
        # This will return False on machines without opencode installed
        result = await backend.health_check()
        # We can't assert True/False since it depends on environment
        # Just verify it returns a boolean without error
        assert isinstance(result, bool)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeHealthCheck -v`

Expected: FAIL with `NotImplementedError`

**Step 3: Implement health_check**

Replace the `health_check` method in `scripts/lib/opencode_backend.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeHealthCheck -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_opencode_backend.py scripts/lib/opencode_backend.py
git commit -m "feat: implement opencode health_check method"
```

---

## Task 5: Test JSONL Response Parsing

**Files:**
- Modify: `tests/test_opencode_backend.py`
- Modify: `scripts/lib/opencode_backend.py`

**Step 1: Add response parsing tests**

Add to `tests/test_opencode_backend.py`:

```python
class TestOpencodeResponseParsing:
    """Tests for JSONL response parsing."""

    def test_parse_text_events(self):
        """Test parsing text events from JSONL output."""
        backend = OpencodeBackend()

        jsonl = '''{"type":"step_start","timestamp":1234,"sessionID":"abc"}
{"type":"text","timestamp":1235,"sessionID":"abc","part":{"text":"Hello "}}
{"type":"text","timestamp":1236,"sessionID":"abc","part":{"text":"world!"}}
{"type":"step_finish","timestamp":1237,"sessionID":"abc","part":{"tokens":{"input":10,"output":5}}}'''

        result = backend._parse_jsonl_response(jsonl)
        assert result == "Hello world!"

    def test_parse_empty_output(self):
        """Test parsing empty output returns empty string."""
        backend = OpencodeBackend()
        assert backend._parse_jsonl_response("") == ""
        assert backend._parse_jsonl_response("   ") == ""

    def test_parse_single_text_event(self):
        """Test parsing single text event."""
        backend = OpencodeBackend()
        jsonl = '{"type":"text","part":{"text":"Single response"}}'
        assert backend._parse_jsonl_response(jsonl) == "Single response"

    def test_parse_invalid_json_lines(self):
        """Test that invalid JSON lines are skipped."""
        backend = OpencodeBackend()
        jsonl = '''{"type":"text","part":{"text":"Valid"}}
not valid json
{"type":"text","part":{"text":" response"}}'''

        result = backend._parse_jsonl_response(jsonl)
        assert result == "Valid response"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeResponseParsing -v`

Expected: FAIL with `AttributeError: 'OpencodeBackend' object has no attribute '_parse_jsonl_response'`

**Step 3: Implement _parse_jsonl_response**

Add to `scripts/lib/opencode_backend.py` (before the `invoke` method):

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeResponseParsing -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_opencode_backend.py scripts/lib/opencode_backend.py
git commit -m "feat: implement JSONL response parsing for opencode backend"
```

---

## Task 6: Test and Implement Invoke Method

**Files:**
- Modify: `tests/test_opencode_backend.py`
- Modify: `scripts/lib/opencode_backend.py`

**Step 1: Add invoke tests**

Add to `tests/test_opencode_backend.py`:

```python
class TestOpencodeInvoke:
    """Tests for invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_cli_not_found(self):
        """Test invoke returns error when CLI not installed."""
        backend = OpencodeBackend()
        response = await backend.invoke("test prompt")

        # On machines without opencode, should return error response
        assert response.agent_id == "gemini-3-pro-preview"
        assert response.role == AgentRole.COUNCIL_MEMBER
        # Either succeeds or returns CLI not found error
        if response.is_error:
            assert "not found" in response.content.lower() or "error" in response.content.lower()

    @pytest.mark.asyncio
    async def test_invoke_returns_agent_response(self):
        """Test invoke returns proper AgentResponse structure."""
        backend = OpencodeBackend(model="github-copilot/test-model")
        response = await backend.invoke("test prompt", role=AgentRole.PRODUCER)

        assert response.agent_id == "test-model"
        assert response.role == AgentRole.PRODUCER
        assert isinstance(response.content, str)
        assert isinstance(response.metadata, dict)

    def test_command_construction(self):
        """Test that command is constructed correctly."""
        backend = OpencodeBackend(model="github-copilot/gemini-3-pro-preview")
        cmd = backend._build_command("test prompt")

        assert cmd[0] == "opencode"
        assert cmd[1] == "run"
        assert "test prompt" in cmd
        assert "-m" in cmd
        assert "github-copilot/gemini-3-pro-preview" in cmd
        assert "--format" in cmd
        assert "json" in cmd
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeInvoke -v`

Expected: FAIL with `NotImplementedError` or `AttributeError`

**Step 3: Implement _build_command and invoke**

Add `_build_command` and replace `invoke` in `scripts/lib/opencode_backend.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_opencode_backend.py::TestOpencodeInvoke -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_opencode_backend.py scripts/lib/opencode_backend.py
git commit -m "feat: implement opencode invoke method"
```

---

## Task 7: Register OpenCode Agents in Registry

**Files:**
- Modify: `tests/test_registry.py`
- Modify: `scripts/lib/registry.py`

**Step 1: Add registry tests for opencode agents**

Add to `tests/test_registry.py` in `TestRegistry` class:

```python
    def test_opencode_agents_registered(self):
        """Test that opencode agents are registered."""
        assert "opencode-gemini" in AGENTS
        assert "opencode-gpt" in AGENTS
        assert "opencode-claude" in AGENTS
```

Add a new test class:

```python
class TestOpencodeBackendInstantiation:
    """Tests for opencode backend instantiation."""

    def test_opencode_gemini_defaults(self):
        """Test opencode-gemini agent configuration."""
        agent = get_agent("opencode-gemini")
        assert agent.name == "opencode"
        assert agent.model == "github-copilot/gemini-3-pro-preview"
        assert agent.agent_id == "gemini-3-pro-preview"

    def test_opencode_gpt_defaults(self):
        """Test opencode-gpt agent configuration."""
        agent = get_agent("opencode-gpt")
        assert agent.name == "opencode"
        assert agent.model == "github-copilot/gpt-5.1-codex"
        assert agent.agent_id == "gpt-5.1-codex"

    def test_opencode_claude_defaults(self):
        """Test opencode-claude agent configuration."""
        agent = get_agent("opencode-claude")
        assert agent.name == "opencode"
        assert agent.model == "github-copilot/claude-sonnet-4.6"
        assert agent.agent_id == "claude-sonnet-4.6"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_registry.py -v`

Expected: FAIL with `KeyError` or agent not found

**Step 3: Update registry to include opencode agents**

Modify `scripts/lib/registry.py`:

```python
"""Agent registry for discovery and instantiation."""

from typing import Optional

from base import AgentBackend
from claude_backend import ClaudeBackend
from codex_backend import CodexBackend
from gemini_backend import GeminiBackend
from opencode_backend import OpencodeBackend


# Registry of available agent backends
AGENTS: dict[str, type[AgentBackend]] = {
    "claude": ClaudeBackend,
    "codex": CodexBackend,
    "gemini": GeminiBackend,
}


def _create_opencode_gemini(**kwargs) -> OpencodeBackend:
    """Factory for opencode-gemini agent."""
    return OpencodeBackend(model="github-copilot/gemini-3-pro-preview", **kwargs)


def _create_opencode_gpt(**kwargs) -> OpencodeBackend:
    """Factory for opencode-gpt agent."""
    return OpencodeBackend(model="github-copilot/gpt-5.1-codex", **kwargs)


def _create_opencode_claude(**kwargs) -> OpencodeBackend:
    """Factory for opencode-claude agent."""
    return OpencodeBackend(model="github-copilot/claude-sonnet-4.6", **kwargs)


# Register opencode agents
AGENTS["opencode-gemini"] = _create_opencode_gemini
AGENTS["opencode-gpt"] = _create_opencode_gpt
AGENTS["opencode-claude"] = _create_opencode_claude


# ... rest of the file unchanged
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/test_registry.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_registry.py scripts/lib/registry.py
git commit -m "feat: register opencode agents in registry"
```

---

## Task 8: Update SKILL.md Documentation

**Files:**
- Modify: `SKILL.md`

**Step 1: Add opencode agents to backend table**

Update the `## Agent Backends` section in `SKILL.md`:

```markdown
## Agent Backends

| Agent | CLI | Default Model |
|-------|-----|---------------|
| claude | `claude -p` | opus |
| codex | `codex exec` | default |
| gemini | `gemini` | gemini-3-pro-preview |
| opencode-gemini | `opencode run` | github-copilot/gemini-3-pro-preview |
| opencode-gpt | `opencode run` | github-copilot/gpt-5.1-codex |
| opencode-claude | `opencode run` | github-copilot/claude-sonnet-4.6 |
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "docs: add opencode agents to SKILL.md"
```

---

## Task 9: Update README.md Documentation

**Files:**
- Modify: `README.md`

**Step 1: Add opencode section to README**

Add after the existing "## Requirements" section:

```markdown
## OpenCode Backend (Optional)

For environments where direct vendor CLIs are blocked but GitHub Copilot access is permitted:

- **OpenCode CLI**: `opencode --version`

OpenCode provides access to multiple AI models through GitHub Copilot:

| Agent | Model | Vendor |
|-------|-------|--------|
| `opencode-gemini` | gemini-3-pro-preview | Google |
| `opencode-gpt` | gpt-5.1-codex | OpenAI |
| `opencode-claude` | claude-sonnet-4.6 | Anthropic |

Example usage:
```bash
# Council with cross-vendor diversity
/tower:council "Review this architecture" --agents claude,opencode-gemini,opencode-gpt

# Debate using OpenCode models
/tower:debate "REST vs GraphQL" --agents opencode-gpt,opencode-gemini
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add opencode backend documentation to README"
```

---

## Task 10: Run Full Test Suite and Final Commit

**Files:**
- All test files

**Step 1: Run full test suite**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m pytest tests/ -v`

Expected: All tests PASS

**Step 2: Verify no linting errors (if applicable)**

Run: `cd /Users/jukim/Developments/Misc/agent-tower-plugin && python -m py_compile scripts/lib/opencode_backend.py`

Expected: No output (success)

**Step 3: Create summary commit (if needed)**

If there are any uncommitted changes:

```bash
git status
# If changes exist:
git add -A
git commit -m "chore: final cleanup for opencode backend"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Test scaffold | `tests/test_opencode_backend.py` |
| 2 | Minimal backend class | `scripts/lib/opencode_backend.py` |
| 3 | Initialization tests | Both files |
| 4 | Health check | Both files |
| 5 | JSONL parsing | Both files |
| 6 | Invoke method | Both files |
| 7 | Registry integration | `registry.py`, `test_registry.py` |
| 8 | SKILL.md docs | `SKILL.md` |
| 9 | README docs | `README.md` |
| 10 | Final verification | All tests |

**Total estimated commits:** 10-12
