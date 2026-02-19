---
description: List available agent backends and their status
allowed-tools: Bash, Read
---

## Overview

This skill lists all registered agent backends and checks their availability by running health checks.

## Your Task

1. Run the list agents script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
   ```

2. Parse the JSON output and present it as a formatted table showing ALL agents from the output:

| Agent | Backend | Status |
|-------|---------|--------|
| (from JSON) | (from JSON) | Available/Unavailable |

3. Report the count: "X of Y agents available"

4. If agents are unavailable, suggest the user check that the CLI tools are installed:
   - `claude --version` for Claude Code CLI
   - `codex --version` for Codex CLI
   - `gemini --version` for Gemini CLI
   - `opencode --version` for OpenCode CLI (provides opencode-gemini, opencode-gpt, opencode-claude)
