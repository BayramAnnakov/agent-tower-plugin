---
description: Adversarial debate with pro/con agents and judge
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

## Overview

The debate mode runs two agents arguing opposing positions (pro and con), then a third agent judges the debate and declares a winner.

**Structure:**
- **Round 1**: Opening arguments (parallel)
- **Round 2-N**: Rebuttals (sequential)
- **Final**: Judge evaluates and declares winner with scores

**Use Cases:**
- Binary decisions (microservices vs monolith, TypeScript vs JavaScript)
- Technology trade-off evaluations
- Architecture decision records
- Pros/cons analysis

## Pre-Execution: Gather Configuration

Before running the debate, use **AskUserQuestion** to confirm configuration options with the user. Ask about:

1. **Number of rounds** - How many argument/rebuttal rounds?
2. **Agent assignments** - Which agents should argue each side?

Example AskUserQuestion usage:
```
Use AskUserQuestion with:
- question: "How many debate rounds should there be?"
- header: "Rounds"
- options:
  - label: "2 rounds", description: "Quick debate - opening + one rebuttal"
  - label: "3 rounds (Recommended)", description: "Balanced depth for most decisions"
  - label: "5 rounds", description: "Thorough exploration of all angles"
```

If the user provided explicit flags in $ARGUMENTS (e.g., `--rounds 2`), skip asking about those options.

## Arguments

Parse these from $ARGUMENTS:
- Question (required) - the binary decision to debate
- `--rounds N` - Number of argument rounds (default: 3)
- `--pro-agent NAME` - Agent for PRO position
- `--con-agent NAME` - Agent for CON position
- `--judge-agent NAME` - Agent to judge the debate
- `--verbose` or `-v` - Show detailed progress

## Available Agents

Check which agents are available:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
```

## Execution

Run the debate:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_debate.py" --question "YOUR_QUESTION_HERE" [--rounds N] [--pro-agent NAME] [--con-agent NAME] [-v]
```

## Output Formatting

Parse the JSON result and present it as:

### Debate: [Question]

**Participants:**
- PRO: [agent name]
- CON: [agent name]
- Judge: [agent name]

---

**Round 1: Opening Arguments**

**PRO** (confidence: X%):
> [Opening argument summary]

Key points:
- Point 1
- Point 2

**CON** (confidence: X%):
> [Opening argument summary]

Key points:
- Point 1
- Point 2

---

**Round 2: Rebuttals**

[Similar format for each round]

---

### Verdict

**Winner: [PRO/CON]** ([winning agent name])

**Scores:** PRO X% | CON Y%

**Reasoning:**
> [Judge's reasoning]

**Key Factors:**
- Factor 1
- Factor 2
- Factor 3

## Example Usage

```
/tower:debate "Should we use microservices or a monolith?"
/tower:debate "Is React better than Vue for this project?" --rounds 2
/tower:debate "Should we prioritize speed or accuracy?" --pro-agent claude --con-agent codex
```
