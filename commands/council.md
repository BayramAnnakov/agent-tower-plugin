---
description: Multi-agent council with parallel opinions and synthesis
allowed-tools: Bash, Read, Glob, Grep
---

## Overview

The council mode runs multiple AI agents in parallel to gather diverse perspectives on a task, then synthesizes their opinions into a final answer.

**Stages:**
1. **Stage 1**: All agents provide independent opinions (parallel)
2. **Stage 2**: Each agent reviews and ranks others' opinions (anonymized)
3. **Stage 3**: Chairman synthesizes all opinions weighted by rankings

**Features:**
- Dynamic persona assignment based on task keywords (Security Analyst, Systems Architect, etc.)
- Anonymized peer ranking to avoid bias
- Weighted synthesis based on peer rankings

## Arguments

Parse these from $ARGUMENTS:
- Task/question (required) - the main argument
- `--agents N` - Number of agents to use (default: all available)
- `--no-personas` - Disable automatic persona assignment
- `--verbose` or `-v` - Show detailed progress

## Available Agents

Check which agents are available:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
```

## Execution

Run the council:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_council.py" --task "YOUR_TASK_HERE" [--agents N] [--no-personas] [-v]
```

## Output Formatting

Parse the JSON result and present it as:

### Council Result - N agents deliberated

**Opinions:**

| Agent | Persona | Opinion Summary | Confidence |
|-------|---------|-----------------|------------|
| claude | Security Analyst | Key finding... | 85% |
| codex | Systems Architect | Key finding... | 90% |
| gemini | Devil's Advocate | Key finding... | 70% |

**Peer Rankings (1=best):**
- Agent A: 1.5 avg rank
- Agent B: 2.0 avg rank

**Chairman's Synthesis:**
> [The synthesized final answer]

**Consensus Level:** X%

**Key Insights:**
- Insight 1
- Insight 2
- Insight 3

**Dissenting Views:**
- [Any notable disagreements]

## Example Usage

```
/tower:council "Should we use TypeScript or JavaScript for the frontend?"
/tower:council "Review the security of this authentication flow" --agents 3
/tower:council "Evaluate this startup idea: AI meal planning" --verbose
```
