"""Live test for the health endpoint (used by Fly/Render/Northflank)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp import ClientSession

from salahbot.health import HealthServer


async def main() -> int:
    port = 18081
    server = HealthServer(port)
    await server.start()
    failures = []
    try:
        async with ClientSession() as session:
            for path in ("/", "/health", "/healthz", "/anything"):
                async with session.get(f"http://127.0.0.1:{port}{path}") as resp:
                    body = await resp.json()
                    ok = resp.status == 200 and body.get("status") == "ok"
                    print(f"[{'PASS' if ok else 'FAIL'}] GET {path} -> {resp.status} {body}")
                    if not ok:
                        failures.append(path)
    finally:
        await server.stop()

    # Disabled when PORT is unset.
    saved = os.environ.pop("PORT", None)
    try:
        assert HealthServer().enabled is False
        print("[PASS] disabled without PORT")
    except AssertionError:
        print("[FAIL] should be disabled without PORT")
        failures.append("port-env")
    finally:
        if saved is not None:
            os.environ["PORT"] = saved

    print()
    print("✅ health endpoint OK" if not failures else f"❌ {len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
