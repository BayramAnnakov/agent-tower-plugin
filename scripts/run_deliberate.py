#!/usr/bin/env python3
"""Run deliberation mode - producer/reviewer consensus loop.

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
from deliberation_mode import DeliberationMode

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
    parser = argparse.ArgumentParser(description="Run producer/reviewer deliberation")
    parser.add_argument("--task", required=True, help="Task for deliberation")
    parser.add_argument("--max-rounds", type=int, default=5, help="Maximum rounds (default: 5)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Consensus threshold (default: 0.85)")
    parser.add_argument("--producer", help="Agent name for producer role")
    parser.add_argument("--reviewer", help="Agent name for reviewer role")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress to stderr")

    args = parser.parse_args()

    # Validate input
    if error := validate_input(args.task):
        print(json.dumps({"error": error}), file=sys.stdout)
        sys.exit(1)

    # Get available agents
    available = await get_available_agents()

    if len(available) < 2:
        print(json.dumps({"error": f"Deliberation requires at least 2 agents, only {len(available)} available"}), file=sys.stdout)
        sys.exit(1)

    # Select agents
    producer_name = args.producer if args.producer and args.producer in available else available[0]
    reviewer_name = args.reviewer if args.reviewer and args.reviewer in available else (
        available[1] if len(available) > 1 else available[0]
    )

    if args.verbose:
        print(f"Available agents: {available}", file=sys.stderr)
        print(f"Producer: {producer_name}, Reviewer: {reviewer_name}", file=sys.stderr)

    producer = get_agent(producer_name)
    reviewer = get_agent(reviewer_name)

    # Run deliberation
    mode = DeliberationMode(
        producer=producer,
        reviewer=reviewer,
        max_rounds=args.max_rounds,
        consensus_threshold=args.threshold,
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
