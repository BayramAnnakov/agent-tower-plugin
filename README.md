# Agent Tower Plugin for Claude Code

Multi-agent deliberation plugin for Claude Code. Orchestrate multiple AI coding assistants (Claude, Codex, Gemini) to get diverse perspectives on tasks.

## Installation

### Quick Install (Recommended)

```bash
npx add-skill https://github.com/BayramAnnakov/agent-tower-plugin
```

### From Marketplace

```bash
# Add the marketplace
claude plugin marketplace add BayramAnnakov/agent-tower-plugin

# Install the plugin
claude plugin install agent-tower-plugin@agent-tower-plugin-marketplace

# Restart Claude Code to activate the plugin
```

### From GitHub

```bash
claude plugin add https://github.com/BayramAnnakov/agent-tower-plugin
```

### From Local Directory

```bash
claude plugin add ./agent-tower-plugin
```

## Requirements

At least 2 of these CLI tools must be installed and accessible:

- **Claude Code CLI**: `claude --version`
- **Codex CLI**: `codex --version`
- **Gemini CLI**: `gemini --version`

## Skills

### `/tower:council` - Multi-Agent Council

Runs multiple agents in parallel, each providing an independent opinion. Before running, Claude analyzes your question and suggests relevant perspectives (personas) via an interactive prompt. Agents anonymously rank each other's responses, and a chairman synthesizes the final answer.

```bash
/tower:council "Should we use TypeScript or JavaScript?"
/tower:council "What's the best fitness program to improve VO2max?"
/tower:council "Evaluate the security of this codebase" --agents 3
```

**Options:**
- `--agents N`: Use N agents (default: all available)
- `--personas JSON`: Custom personas as JSON array
- `--no-personas`: Disable persona assignment
- `-v, --verbose`: Show detailed progress

### `/tower:debate` - Adversarial Debate

Two agents argue opposing positions on a binary decision. A judge evaluates and declares a winner.

```bash
/tower:debate "Microservices vs monolith?"
/tower:debate "React vs Vue for this project?" --rounds 2
```

**Options:**
- `--rounds N`: Number of argument rounds (default: 3)
- `--pro-agent NAME`: Agent for PRO position
- `--con-agent NAME`: Agent for CON position
- `--judge-agent NAME`: Agent to judge
- `-v, --verbose`: Show detailed progress

### `/tower:deliberate` - Producer/Reviewer Loop

A producer generates a response, a reviewer provides feedback, and they iterate until consensus.

```bash
/tower:deliberate "Review the architecture of ~/GH/myproject"
/tower:deliberate "Analyze this PR" --max-rounds 3 --threshold 0.9
```

**Options:**
- `--max-rounds N`: Maximum rounds (default: 5)
- `--threshold X`: Consensus threshold 0.0-1.0 (default: 0.85)
- `--producer NAME`: Agent for producer role
- `--reviewer NAME`: Agent for reviewer role
- `-v, --verbose`: Show detailed progress

### `/tower:agents` - List Available Agents

Check which agent backends are available.

```bash
/tower:agents
```

## Architecture

```
agent-tower-plugin/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest
├── commands/
│   ├── council.md            # /tower:council skill
│   ├── debate.md             # /tower:debate skill
│   ├── deliberate.md         # /tower:deliberate skill
│   └── agents.md             # /tower:agents skill
├── scripts/
│   ├── lib/                  # Core library modules
│   │   ├── base.py           # AgentBackend ABC
│   │   ├── claude_backend.py
│   │   ├── codex_backend.py
│   │   ├── gemini_backend.py
│   │   ├── registry.py       # Agent discovery
│   │   ├── personas.py       # Dynamic persona assignment
│   │   ├── council_mode.py   # Council orchestration
│   │   ├── debate_mode.py    # Debate orchestration
│   │   └── deliberation_mode.py
│   ├── run_council.py        # Entry point for council
│   ├── run_debate.py         # Entry point for debate
│   ├── run_deliberate.py     # Entry point for deliberation
│   └── list_agents.py        # Entry point for agents
├── SKILL.md                  # Skill context for Claude
└── README.md
```

## How It Works

### Council Mode

1. **Pre-flight - Persona Selection**: Claude analyzes your question and suggests relevant perspectives via an interactive prompt. You select which personas to use (e.g., "Exercise Physiologist", "Local Expert", "Critical Thinker").

2. **Stage 1 - Opinions**: All agents analyze the task in parallel with their assigned personas.

3. **Stage 2 - Ranking**: Each agent reviews and ranks others' responses. Responses are anonymized (A, B, C) to avoid bias.

4. **Stage 3 - Synthesis**: A chairman agent synthesizes all opinions, weighted by peer rankings, into a final answer.

### Debate Mode

1. **Opening**: Both agents present opening arguments in parallel.
2. **Rebuttals**: Agents take turns responding to each other's arguments.
3. **Judgment**: A judge evaluates both sides and declares a winner with scores.

### Deliberation Mode

1. **Initial**: Producer generates first response.
2. **Review Loop**: Reviewer provides structured feedback, producer addresses it.
3. **Consensus Check**: Each round checks if agreement exceeds threshold.

## Dynamic Personas

Claude analyzes your question and suggests relevant personas. You can also use custom personas via the `--personas` flag.

### Technical Personas (for code/architecture questions)

| Persona | Focus Areas |
|---------|-------------|
| Security Analyst | auth, vulnerabilities, OWASP, injection |
| Systems Architect | scalability, performance, infrastructure |
| Code Quality Reviewer | refactoring, testing, patterns |
| DevOps Engineer | deployment, kubernetes, monitoring |
| Data Engineer | databases, schemas, pipelines |
| Devil's Advocate | risks, assumptions, edge cases |

### Generalist Personas (for non-technical questions)

| Persona | Focus Areas |
|---------|-------------|
| Research Analyst | facts, sources, evidence, accuracy |
| Local Expert | practical tips, insider knowledge, logistics |
| Critical Thinker | assumptions, trade-offs, nuance |
| Practical Advisor | actionable advice, common pitfalls |

### Business Personas

| Persona | Focus Areas |
|---------|-------------|
| Business Strategist | market, monetization, growth |
| Product Manager | user needs, features, roadmap |
| Financial Analyst | pricing, margins, projections |
| UX Designer | usability, accessibility, flows |

## License

MIT
