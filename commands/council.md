---
description: Multi-agent council with parallel opinions and synthesis
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

## Overview

The council mode runs multiple AI agents in parallel to gather diverse perspectives on a task, then synthesizes their opinions into a final answer.

**Stages:**
1. **Stage 1**: All agents provide independent opinions (parallel)
2. **Stage 2**: Each agent reviews and ranks others' opinions (anonymized)
3. **Stage 3**: Chairman synthesizes all opinions weighted by rankings

**Features:**
- Dynamic persona suggestion based on question analysis
- Anonymized peer ranking to avoid bias
- Weighted synthesis based on peer rankings

## Pre-Execution: Analyze Question & Gather Configuration

Before running the council:

### 1. Analyze the Question
First, analyze the user's question to determine appropriate perspectives/personas. Consider:
- **Technical questions** (code, architecture, security) → technical personas (Security Analyst, Systems Architect, Code Reviewer, etc.)
- **Business questions** (strategy, market, product) → business personas (Business Strategist, Product Manager, Financial Analyst, etc.)
- **General knowledge questions** (recommendations, advice, comparisons) → generalist personas (Research Analyst, Local Expert, Practical Advisor, Critical Thinker)
- **Creative questions** → creative personas (Creative Director, User Advocate, Trend Analyst)

### 2. Suggest Personas via AskUserQuestion
Use **AskUserQuestion** to suggest relevant personas based on your analysis:

```
Use AskUserQuestion with:
- question: "I've analyzed your question. Which perspectives would be most valuable?"
- header: "Perspectives"
- multiSelect: true
- options: [Generate 3-4 relevant personas based on the question type]

Example for "best hiking in Seattle":
  - label: "Local Expert", description: "Deep knowledge of Seattle area trails and conditions"
  - label: "Outdoor Enthusiast", description: "Practical hiking experience and recommendations"
  - label: "Research Analyst", description: "Comprehensive data on trail ratings and reviews"
  - label: "Critical Thinker", description: "Questions assumptions about 'best' and considers trade-offs"

Example for "should we use microservices":
  - label: "Systems Architect", description: "Scalability, infrastructure, distributed systems"
  - label: "DevOps Engineer", description: "Deployment, monitoring, operational complexity"
  - label: "Developer Experience", description: "Team productivity, learning curve, tooling"
  - label: "Devil's Advocate", description: "Challenge assumptions, identify hidden risks"
```

### 3. Number of Agents
Also ask about number of agents if not specified:
```
Use AskUserQuestion with:
- question: "How many agents should participate?"
- header: "Agents"
- options:
  - label: "2 agents", description: "Quick analysis with two perspectives"
  - label: "3 agents (Recommended)", description: "Balanced coverage"
  - label: "All available", description: "Maximum perspectives"
```

Skip questions for options explicitly provided in $ARGUMENTS.

## Arguments

Parse these from $ARGUMENTS:
- Task/question (required) - the main argument
- `--agents N` - Number of agents to use (default: all available)
- `--personas JSON` - Custom personas as JSON array (see below)
- `--no-personas` - Disable automatic persona assignment
- `--verbose` or `-v` - Show detailed progress

## Available Agents

Check which agents are available:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/list_agents.py"
```

## Execution

Run the council with custom personas (based on user selections):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_council.py" --task "YOUR_TASK_HERE" --personas '[{"name":"Local Expert","focus":"Seattle area knowledge"},{"name":"Outdoor Enthusiast","focus":"hiking experience"},{"name":"Critical Thinker","focus":"trade-offs and nuance"}]' [--agents N] [-v]
```

Or run with automatic persona inference:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_council.py" --task "YOUR_TASK_HERE" [--agents N] [-v]
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
