#!/usr/bin/env python3
"""List available agent backends with health check status.

Cross-platform compatible (Windows, macOS, Linux).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add lib to path (cross-platform)
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from registry import AGENTS, get_agent


async def main():
    """Check availability of all registered agents."""
    results = []

    for name in AGENTS.keys():
        try:
            agent = get_agent(name)
            available = await agent.health_check()
            results.append({
                "name": name,
                "available": available,
                "backend": agent.__class__.__name__,
            })
        except Exception as e:
            results.append({
                "name": name,
                "available": False,
                "error": str(e),
            })

    # Output JSON result
    output = {
        "agents": results,
        "available_count": sum(1 for r in results if r["available"]),
        "total_count": len(results),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    # Windows compatibility: use WindowsSelectorEventLoopPolicy for subprocess
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
