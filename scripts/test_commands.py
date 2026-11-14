"""
Load every cog and verify the slash-command tree without connecting.

    python scripts/test_commands.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from salahbot.bot import COGS, SalahBot  # noqa: E402
from salahbot.config import Settings  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


async def main() -> int:
    bot = SalahBot(Settings(token="dummy-token"))

    for extension in COGS:
        try:
            await bot.load_extension(extension)
            check(f"load {extension}", True)
        except Exception as exc:  # noqa: BLE001
            check(f"load {extension}", False, f"{type(exc).__name__}: {exc}")

    commands = {cmd.name: cmd for cmd in bot.tree.get_commands()}
    expected_toplevel = {
        "help",
        "ping",
        "methods",
        "about",
        "prayer",
        "next",
        "week",
        "settings",
        "azkar",
        "zikr",
        "azkar_reminder",
    }
    check(
        "all top-level commands registered",
        expected_toplevel <= set(commands),
        f"missing {expected_toplevel - set(commands)}",
    )
    check("no unexpected commands", set(commands) <= expected_toplevel, str(set(commands) - expected_toplevel))

    for name, cmd in commands.items():
        if not hasattr(cmd, "parameters"):
            continue
        check(f"/{name} has description", bool(cmd.description), cmd.description)

    # -- parameters ------------------------------------------------------- #
    prayer = commands.get("prayer")
    params = {p.name for p in prayer.parameters} if prayer else set()
    check("/prayer params", {"city", "day", "method"} <= params, str(params))

    azkar = commands.get("azkar")
    params = {p.name for p in azkar.parameters} if azkar else set()
    check("/azkar has category", "category" in params, str(params))
    choices = azkar.parameters[0].choices if azkar else []
    check("/azkar 5 choices", len(choices) == 5, str(len(choices)))

    # -- settings subgroup ------------------------------------------------- #
    settings = commands.get("settings")
    sub = {c.name for c in getattr(settings, "commands", [])}
    check(
        "/settings subcommands",
        {"city", "method", "reminders", "show"} <= sub,
        str(sub),
    )

    # -- cogs -------------------------------------------------------------- #
    check("3 cogs loaded", len(bot.cogs) == 3, str(list(bot.cogs)))
    check("reminder loop exists", any(
        "reminder_loop" in dir(cog) for cog in bot.cogs.values()
    ))

    # -- autocomplete ------------------------------------------------------ #
    from types import SimpleNamespace

    from salahbot.cogs.prayer import _autocomplete_city

    dummy = SimpleNamespace()
    empty = await _autocomplete_city(dummy, "")
    check("autocomplete empty -> 25", len(empty) == 25, str(len(empty)))
    exact = await _autocomplete_city(dummy, "القاهرة")
    check("autocomplete exact match first", bool(exact) and exact[0].value == "القاهرة")
    partial = await _autocomplete_city(dummy, "أس")
    check("autocomplete arabic prefix", any(c.value == "أسوان" for c in partial))

    await bot.shutdown_services()
    for extension in COGS:
        try:
            await bot.unload_extension(extension)
        except Exception:  # noqa: BLE001
            pass
    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} failure(s)")
        return 1
    print("✅ command tree OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
