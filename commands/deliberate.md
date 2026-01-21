---
description: Producer/reviewer deliberation until consensus
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

## Overview

The deliberation mode runs a producer and reviewer agent in sequential rounds until they reach consensus or hit the maximum rounds.

**Structure:**
- **Round 1**: Producer generates initial response
- **Round 2-N**: Reviewer provides feedback, producer responds
- **Consensus Check**: Each round checks if agreement level exceeds threshold

**Use Cases:**
- Code review and iterative refinement
- Document review with feedback cycles
- Architecture proposals with critique
- Any task benefiting from structured feedback

## Pre-Execution: Gather Configuration

Before running the deliberation, use **AskUserQuestion** to confirm configuration options with the user. Ask about:

1. **Maximum rounds** - How many rounds before stopping if no consensus?
2. **Consensus threshold** - How strict should the agreement requirement be?
3. **Agent roles** - Which agents should be producer vs reviewer?

Example AskUserQuestion usage:
```
Use AskUserQuestion with:
- question: "How many deliberation rounds maximum?"
- header: "Max Rounds"
- options:
  - label: "3 rounds", description: "Quick iteration, may not reach full consensus"
  - label: "5 rounds (Recommended)", description: "Balanced depth for most tasks"
  - label: "7 rounds", description: "Thorough refinement for complex tasks"
```

```
Use AskUserQuestion with:
- question: "How strict should the consensus threshold be?"
- header: "Threshold"
- options:
  - label: "80%", description: "More lenient - faster consensus"
  - label: "85% (Recommended)", description: "Balanced - good agreement level"
  - label: "90%", description: "Strict - higher quality but may not reach consensus"
```

If the user provided explicit flags in $ARGUMENTS (e.g., `--max-rounds 3`), skip asking about those options.

## Arguments

Parse these from $ARGUMENTS:
- Task (required) - the task for deliberation
- `--max-rounds N` - Maximum rounds before stopping (default: 5)
- `--threshold X` - Consensus threshold 0.0-1.0 (default: 0.85)
- `--producer NAME` - Agent for producer role
- `--reviewer NAME` - Agent for reviewer role
- `--verbose` or `-v` - Show detailed progress

## Available Agents

Check which agents are available:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
```

## Execution

Run the deliberation:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_deliberate.py" --task "YOUR_TASK_HERE" [--max-rounds N] [--threshold X] [--producer NAME] [--reviewer NAME] [-v]
```

## Output Formatting

Parse the JSON result and present it based on the status:

### If Consensus Reached:

**Deliberation Complete - Consensus at Round N**

**Participants:**
- Producer: [agent name]
- Reviewer: [agent name]

**Agreement Level:** X%

**Final State:**
[Summary of the final agreed-upon position]

**Key Feedback Points Addressed:**
- [Feedback that was incorporated]

---

### If Max Rounds Reached:

**Deliberation Complete - No Consensus After N Rounds**

**Participants:**
- Producer: [agent name]
- Reviewer: [agent name]

**Final Agreement Level:** X%

**Remaining Disputes:**
- [Points that couldn't be resolved]

**Recommendations:**
- Consider manual review of disputed points
- May need human decision-making

---

### Round-by-Round Summary (if verbose):

**Round 1: Initial Response**
- Producer generated response (X chars)

**Round 2: Review**
- Reviewer found N points (X critical, Y major, Z minor)
- Agreement level: X%

**Round 2: Response**
- Producer agreed with N points
- Producer disputed M points

[Continue for each round]

## Example Usage

```
/tower:deliberate "Review the architecture of ~/GH/myproject"
/tower:deliberate "Analyze this pull request" --max-rounds 3 --threshold 0.9
/tower:deliberate "Evaluate this API design" --producer claude --reviewer codex --verbose
```
