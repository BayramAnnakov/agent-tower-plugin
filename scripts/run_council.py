#!/usr/bin/env python3
"""Run council mode - parallel opinions with chairman synthesis.

Cross-platform compatible (Windows, macOS, Linux).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add lib to path (cross-platform)
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from registry import get_agent, get_available_agents
from council_mode import CouncilMode

# Security: Maximum input length to prevent resource exhaustion
MAX_TASK_LENGTH = 100_000  # 100KB


def validate_input(task: str) -> str | None:
    """Validate task input. Returns error message or None if valid."""
    if not task or not task.strip():
        return "Task cannot be empty"
    if len(task) > MAX_TASK_LENGTH:
        return f"Task too long ({len(task)} chars). Maximum: {MAX_TASK_LENGTH}"
    return None


async def main():
    parser = argparse.ArgumentParser(description="Run multi-agent council deliberation")
    parser.add_argument("--task", required=True, help="Task/question for the council")
    parser.add_argument("--agents", type=int, default=0, help="Number of agents (0=all available)")
    parser.add_argument("--agent-names", help="Comma-separated list of specific agents to use (e.g., 'claude,codex,gemini')")
    parser.add_argument("--no-personas", action="store_true", help="Disable dynamic persona assignment")
    parser.add_argument("--personas", help="Custom personas as JSON array: '[{\"name\":\"Expert\",\"focus\":\"topic\"}]'")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress to stderr")

    args = parser.parse_args()

    # Validate input
    if error := validate_input(args.task):
        print(json.dumps({"error": error}), file=sys.stdout)
        sys.exit(1)

    # Parse custom personas if provided
    custom_personas = None
    if args.personas:
        try:
            custom_personas = json.loads(args.personas)
            if not isinstance(custom_personas, list):
                print(json.dumps({"error": "Personas must be a JSON array"}), file=sys.stdout)
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid personas JSON: {e}"}), file=sys.stdout)
            sys.exit(1)

    # Get available agents
    available = await get_available_agents()

    if not available:
        print(json.dumps({"error": "No agents available"}), file=sys.stdout)
        sys.exit(1)

    if len(available) < 2:
        print(json.dumps({"error": f"Council requires at least 2 agents, only {len(available)} available"}), file=sys.stdout)
        sys.exit(1)

    # Select agents
    if args.agent_names:
        # Use specific agents by name
        requested_names = [name.strip() for name in args.agent_names.split(",")]
        invalid_names = [name for name in requested_names if name not in available]
        if invalid_names:
            print(json.dumps({"error": f"Unknown agents: {invalid_names}. Available: {available}"}), file=sys.stdout)
            sys.exit(1)
        selected_agents = requested_names
    else:
        # Use count-based selection
        num_agents = args.agents if args.agents > 0 else len(available)
        num_agents = min(num_agents, len(available))
        selected_agents = available[:num_agents]

    if args.verbose:
        print(f"Available agents: {available}", file=sys.stderr)
        print(f"Using agents: {selected_agents}", file=sys.stderr)
        if custom_personas:
            print(f"Using custom personas: {custom_personas}", file=sys.stderr)

    members = [get_agent(name) for name in selected_agents]

    # Run council
    mode = CouncilMode(
        members=members,
        chairman=members[0],
        use_personas=not args.no_personas,
        custom_personas=custom_personas,
        verbose=args.verbose,
    )

    result = await mode.run(args.task)

    # Output JSON result
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    # Windows compatibility: use WindowsSelectorEventLoopPolicy for subprocess
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
