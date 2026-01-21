---
description: List available agent backends and their status
allowed-tools: Bash, Read
---

## Overview

This skill lists all registered agent backends (Claude, Codex, Gemini) and checks their availability by running health checks.

## Your Task

1. Run the list agents script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
   ```

2. Parse the JSON output and present it as a formatted table:

| Agent | Backend | Status |
|-------|---------|--------|
| claude | ClaudeBackend | Available/Unavailable |
| codex | CodexBackend | Available/Unavailable |
| gemini | GeminiBackend | Available/Unavailable |

3. Report the count: "X of Y agents available"

4. If no agents are available, suggest the user check that the CLI tools are installed:
   - `claude --version` for Claude Code CLI
   - `codex --version` for Codex CLI
   - `gemini --version` for Gemini CLI
