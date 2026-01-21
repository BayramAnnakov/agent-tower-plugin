#!/usr/bin/env python3
"""Run debate mode - adversarial pro/con argumentation.

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
from debate_mode import DebateMode

# Security: Maximum input length to prevent resource exhaustion
MAX_QUESTION_LENGTH = 100_000  # 100KB


def validate_input(question: str) -> str | None:
    """Validate question input. Returns error message or None if valid."""
    if not question or not question.strip():
        return "Question cannot be empty"
    if len(question) > MAX_QUESTION_LENGTH:
        return f"Question too long ({len(question)} chars). Maximum: {MAX_QUESTION_LENGTH}"
    return None


async def main():
    parser = argparse.ArgumentParser(description="Run adversarial debate between agents")
    parser.add_argument("--question", required=True, help="Binary decision question to debate")
    parser.add_argument("--rounds", type=int, default=3, help="Number of argument rounds (default: 3)")
    parser.add_argument("--pro-agent", help="Agent name for PRO position")
    parser.add_argument("--con-agent", help="Agent name for CON position")
    parser.add_argument("--judge-agent", help="Agent name for judge (default: first available)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress to stderr")

    args = parser.parse_args()

    # Validate input
    if error := validate_input(args.question):
        print(json.dumps({"error": error}), file=sys.stdout)
        sys.exit(1)

    # Get available agents
    available = await get_available_agents()

    if len(available) < 2:
        print(json.dumps({"error": f"Debate requires at least 2 agents, only {len(available)} available"}), file=sys.stdout)
        sys.exit(1)

    # Select agents
    pro_name = args.pro_agent if args.pro_agent and args.pro_agent in available else available[0]
    con_name = args.con_agent if args.con_agent and args.con_agent in available else (
        available[1] if len(available) > 1 else available[0]
    )
    judge_name = args.judge_agent if args.judge_agent and args.judge_agent in available else available[0]

    if args.verbose:
        print(f"Available agents: {available}", file=sys.stderr)
        print(f"PRO: {pro_name}, CON: {con_name}, Judge: {judge_name}", file=sys.stderr)

    pro_agent = get_agent(pro_name)
    con_agent = get_agent(con_name)
    judge_agent = get_agent(judge_name)

    # Run debate
    mode = DebateMode(
        pro_agent=pro_agent,
        con_agent=con_agent,
        judge=judge_agent,
        max_rounds=args.rounds,
        verbose=args.verbose,
    )

    result = await mode.run(args.question)

    # Output JSON result
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    # Windows compatibility: use WindowsSelectorEventLoopPolicy for subprocess
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
