# Agent Tower Plugin

Multi-agent deliberation for Claude Code. Orchestrate multiple AI coding assistants (Claude, Codex, Gemini) to get diverse perspectives on tasks.

## Available Skills

### `/tower:council`
**Multi-agent council with parallel opinions and synthesis**

Runs multiple agents in parallel, each providing an independent opinion with a dynamically assigned expert persona. Agents then anonymously rank each other's responses, and a chairman synthesizes the final answer.

Best for: Evaluations, strategy decisions, comprehensive analysis

### `/tower:debate`
**Adversarial debate with pro/con agents**

Two agents argue opposing positions on a binary decision. A judge evaluates the arguments and declares a winner with scores.

Best for: Binary decisions, trade-off analysis, technology choices

### `/tower:deliberate`
**Producer/reviewer consensus loop**

A producer generates a response, a reviewer provides structured feedback, and they iterate until reaching consensus or hitting max rounds.

Best for: Code review, document refinement, iterative improvement

### `/tower:agents`
**List available agents**

Shows which agent backends (Claude, Codex, Gemini) are currently available.

## Agent Backends

| Agent | CLI | Default Model |
|-------|-----|---------------|
| claude | `claude -p` | opus |
| codex | `codex exec` | default |
| gemini | `gemini` | gemini-3-pro-preview |

## Dynamic Personas

Council mode assigns expert personas based on task keywords:

| Persona | Trigger Keywords |
|---------|------------------|
| Security Analyst | auth, vulnerability, owasp, injection |
| Systems Architect | scalability, performance, infrastructure |
| Code Quality Reviewer | refactor, maintainability, testing |
| Business Strategist | market, monetization, growth, startup |
| Devil's Advocate | (auto-included for 3+ agents) |

## Examples

```
/tower:council "Evaluate this startup idea: AI-powered meal planning"
/tower:debate "Should we use microservices or a monolith?"
/tower:deliberate "Review the security of ~/GH/myproject"
/tower:agents
```
