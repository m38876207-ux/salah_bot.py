"""Entry point: ``python -m salahbot``.

The token is read from the ``DISCORD_TOKEN`` environment variable (a ``.env``
file next to this project works too).  Nothing else is required to start.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import discord

# Allow ``python salahbot/__main__.py`` as well as ``python -m salahbot``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from salahbot.bot import COGS, SalahBot  # noqa: E402
from salahbot.config import PROJECT_DIR, load_settings  # noqa: E402
from salahbot.prayer_times import METHODS  # noqa: E402

BANNER = r"""
   _____      __      __        ____        _
  / ___/____ _/ /___  / /_      / __ )____  (_)
  \__ \/ __ `/ / __ \/ __ \    / __  / __ \/ /
 ___/ / /_/ / / /_/ / /_/ /   / /_/ / /_/ / /
/____/\__,_/_/ .___/_.___/   /_____/\____/_/
            /_/
"""


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    # This bot has no voice features; those two warnings are pure noise.
    logging.getLogger("discord.client").setLevel(logging.ERROR)


def _preflight() -> bool:
    """Print a configuration report and return whether we can start."""
    settings = load_settings()
    print(BANNER)
    print(f"  project     : {PROJECT_DIR}")
    print(f"  python      : {sys.version.split()[0]}")
    print(f"  extensions  : {', '.join(COGS)}")
    print(f"  methods     : {', '.join(METHODS)}")
    print(f"  default city: {settings.default_city}")
    print(f"  guild scope : {'single guild ' + str(settings.guild_id) if settings.guild_id else 'global'}")
    if not settings.token:
        print("\n  [X] DISCORD_TOKEN is not set.")
        print("      Put your bot token in a .env file next to main.py:")
        print("          DISCORD_TOKEN=your-token-here")
        return False
    print(f"  token       : {settings.token[:6]}… ({len(settings.token)} chars)")
    print("\n  [OK] configuration looks good — starting the bot.\n")
    return True


async def _run() -> int:
    settings = load_settings()
    bot = SalahBot(settings)
    try:
        await bot.start(settings.token)
    except KeyboardInterrupt:
        pass
    finally:
        await bot.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="salahbot", description="Discord bot for Egyptian prayer times and adhkar"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the configuration and exit without connecting",
    )
    args = parser.parse_args(argv)

    _setup_logging(load_settings().log_level)
    ok = _preflight()
    if args.check or not ok:
        return 0 if ok else 1

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nstopped.")
        return 0
    except discord.LoginFailure:
        print(
            "\n  [X] Discord rejected the token.\n"
            "      * did you paste the whole token from Bot -> Reset Token?\n"
            "      * is it the *bot* token and not the client secret?\n"
        )
        return 1
    except discord.PrivilegedIntentsRequired:
        print(
            "\n  [X] A privileged intent is required.\n"
            "      Enable it in the Developer Portal (Bot -> Privileged Gateway Intents).\n"
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - surface login errors clearly
        logging.getLogger("salahbot").exception("fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
