# OpenCode Backend Design

**Date:** 2026-02-19
**Status:** Approved

## Overview

Add an OpenCode backend to Agent Tower, enabling access to multiple AI models (Gemini, GPT, Claude) through the `opencode` CLI. This addresses environments where direct vendor CLIs (like `gemini`) are blocked but access is permitted through GitHub Copilot via opencode.

## Motivation

- Company policy blocks direct `gemini` CLI due to authentication/compliance requirements
- `opencode` CLI provides approved access to multiple AI models through GitHub Copilot
- Adding opencode backend enables cross-vendor AI diversity (Google, OpenAI, Anthropic) through one approved tool

## Design

### OpenCode CLI Interface

**Command pattern:**
```bash
opencode run "<prompt>" -m <provider/model> --format json
```

**JSON output format (JSONL):**
```json
{"type":"step_start","timestamp":...,"sessionID":"...","part":{...}}
{"type":"text","timestamp":...,"sessionID":"...","part":{"text":"<response>",...}}
{"type":"step_finish","timestamp":...,"sessionID":"...","part":{"tokens":{...},...}}
```

**Key models available via GitHub Copilot:**
| Model ID | Vendor |
|----------|--------|
| `github-copilot/gemini-3-pro-preview` | Google |
| `github-copilot/gpt-5.1-codex` | OpenAI |
| `github-copilot/claude-sonnet-4.6` | Anthropic |

### OpencodeBackend Class

**File:** `scripts/lib/opencode_backend.py`

```python
class OpencodeBackend(AgentBackend):
    """Backend for opencode CLI.

    Wraps `opencode run` command for non-interactive AI invocation.
    Supports any model available through opencode (GitHub Copilot, Bedrock, OpenAI).
    """

    name = "opencode"

    def __init__(
        self,
        model: str = "github-copilot/gemini-3-pro-preview",
        timeout: int = 600,
    ):
        self.model = model
        self.timeout = timeout
        # Short name for display (e.g., "gemini-3-pro-preview")
        self.agent_id = model.split("/")[-1]

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke opencode CLI with the given prompt."""
        cmd = [
            "opencode", "run",
            prompt,
            "-m", self.model,
            "--format", "json",
        ]
        # ... subprocess execution and response parsing

    async def health_check(self) -> bool:
        """Check if opencode CLI is available."""
        # Run: opencode --version
```

**Response parsing:**
- Parse JSONL output line by line
- Extract text from `type: "text"` events via `part.text`
- Aggregate multiple text events for complete response
- Extract token usage from `type: "step_finish"` event

### Agent Registration

**File:** `scripts/lib/registry.py`

Register pre-configured opencode agents for common use cases:

```python
from opencode_backend import OpencodeBackend

AGENTS: dict[str, type[AgentBackend]] = {
    # Existing backends
    "claude": ClaudeBackend,
    "codex": CodexBackend,
    "gemini": GeminiBackend,

    # New opencode-backed agents
    "opencode-gemini": lambda **kw: OpencodeBackend(
        model="github-copilot/gemini-3-pro-preview", **kw
    ),
    "opencode-gpt": lambda **kw: OpencodeBackend(
        model="github-copilot/gpt-5.1-codex", **kw
    ),
    "opencode-claude": lambda **kw: OpencodeBackend(
        model="github-copilot/claude-sonnet-4.6", **kw
    ),
}
```

### Usage Examples

```bash
# Council with three different AI vendors
/tower:council "Review this architecture" --agents claude,opencode-gemini,opencode-gpt

# Deliberate with Gemini (via opencode) as reviewer
/tower:deliberate "Review the plan" --producer claude --reviewer opencode-gemini

# Debate between OpenAI and Google
/tower:debate "REST vs GraphQL" --agents opencode-gpt,opencode-gemini

# Check available agents
/tower:agents
```

## Files to Change

| File | Action | Description |
|------|--------|-------------|
| `scripts/lib/opencode_backend.py` | Create | New backend class |
| `scripts/lib/registry.py` | Modify | Register opencode agents |
| `SKILL.md` | Modify | Document new agents in backend table |
| `commands/agents.md` | Modify | Add opencode to health check output |
| `README.md` | Modify | Document opencode backend and setup |

## Testing

1. **Unit tests:** `tests/test_opencode_backend.py`
   - Test command construction
   - Test JSON response parsing
   - Test error handling (timeout, CLI not found)

2. **Integration tests:**
   - Health check with real opencode CLI
   - Simple invocation test
   - Multi-agent council test

## Installation

After implementation, users can install from the fork:

```bash
# Update Claude Code plugin to use fork
# (specific steps depend on Claude Code plugin management)
```

Or submit as PR to upstream once validated.

## Design Decisions

1. **Runtime `--model` flag?** → **Deferred.** Start with three pre-configured agents. Users needing custom models can fork and edit registry. Add flag later if demand emerges.

2. **Dynamic agent discovery from `opencode models`?** → **Deferred.** Hardcoded agents are more predictable and avoid startup latency/failure modes. Three agents (Gemini, GPT, Claude) cover the vendor diversity use case.

3. **Rate limiting for GitHub Copilot API?** → **Not implementing.** Consistent with existing backends (Claude, Codex, Gemini) which don't implement rate limiting. Add retry logic later if it becomes a pain point.
