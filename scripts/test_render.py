"""
Simulate startup and the exact payloads Discord would receive.

A fake `Interaction` captures embed/view objects, and a fake `Gateway` captures
the tree sync payload, so we can validate titles, field counts, colours, and
component structure without a token or network.

    python scripts/test_render.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord  # noqa: E402

from salahbot.bot import COGS, SalahBot  # noqa: E402
from salahbot.config import Settings  # noqa: E402
from salahbot.ui.views import PrayerView  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


class FakeResponse:
    def __init__(self) -> None:
        self.message_kwargs: list[dict] = []
        self.deferred = False

    async def send_message(self, content=None, **kwargs) -> None:
        self.message_kwargs.append({"content": content, **kwargs})

    async def defer(self) -> None:
        self.deferred = True

    def is_done(self) -> bool:
        return self.deferred or bool(self.message_kwargs)


class FakeInteraction:
    def __init__(self, user_id: int = 7, guild_id: int | None = 123) -> None:
        self.user = discord.Object(id=user_id)
        self.user.display_name = "Tester"  # type: ignore[attr-defined]
        self.guild_id = guild_id
        self.guild = discord.Object(id=guild_id) if guild_id else None
        self.response = FakeResponse()
        self.followup = _FakeFollowup(self.response)

    def __getattr__(self, name):  # pragma: no cover - safety net
        raise AttributeError(name)


class _FakeFollowup:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    async def send(self, content=None, **kwargs) -> None:
        self._response.message_kwargs.append({"content": content, **kwargs})


def payload(interaction: FakeInteraction) -> dict:
    assert interaction.response.message_kwargs, "nothing was sent"
    return interaction.response.message_kwargs[-1]


async def main() -> int:
    bot = SalahBot(Settings(token="dummy-token"))
    for extension in COGS:
        await bot.load_extension(extension)

    # -- /help ------------------------------------------------------------ #
    general = bot.cogs["General"]
    interaction = FakeInteraction()
    await general.help.callback(general, interaction)  # type: ignore[attr-defined]
    sent = payload(interaction)
    check("/help sends an embed", isinstance(sent["embed"], discord.Embed))
    check("/help is ephemeral", sent.get("ephemeral") is True)
    help_text = (sent["embed"].description or "") + "".join(
        field.value for field in sent["embed"].fields
    )
    check("/help mentions /prayer", "/prayer" in help_text, help_text[:120])
    check("/help mentions /azkar", "/azkar" in help_text)

    # -- /prayer ---------------------------------------------------------- #
    prayer_cog = bot.cogs["Prayer"]
    interaction = FakeInteraction()
    await prayer_cog.prayer.callback(prayer_cog, interaction, None, None, None)
    sent = payload(interaction)
    embed = sent["embed"]
    view = sent.get("view")
    check("/prayer defers", interaction.response.deferred)
    check("/prayer title has city", "مواقيت الصلاة" in (embed.title or ""))
    check("/prayer has 2 fields (table + next)", len(embed.fields) == 2, str(len(embed.fields)))
    check("/prayer table lists all 6 times", embed.fields[0].value.count("`") >= 6)
    check("/prayer next-prayer countdown", "الصلاة القادمة" in embed.fields[1].name)
    check("/prayer has a day-navigation view", isinstance(view, PrayerView))
    check("/prayer view has 3 buttons", len(view.children) == 3)
    check("embed colour is green", embed.colour.value == 0x1F8B4C, hex(embed.colour.value))
    check("embed under 6000 chars", len(embed) <= 6000, str(len(embed)))
    check("footer has the tagline", "مصر" in (embed.footer.text or ""))

    # -- /next ------------------------------------------------------------ #
    interaction = FakeInteraction()
    await prayer_cog.next_prayer.callback(prayer_cog, interaction, None)
    sent = payload(interaction)
    check("/next sends an embed", isinstance(sent["embed"], discord.Embed))
    check("/next shows a countdown", "بعد" in sent["embed"].description)

    # -- /week ------------------------------------------------------------ #
    interaction = FakeInteraction()
    await prayer_cog.week.callback(prayer_cog, interaction, None, None)
    sent = payload(interaction)
    lines = sent["embed"].description.strip().splitlines()
    check("/week has header + 7 rows", len(lines) == 8, str(len(lines)))

    # -- /azkar ----------------------------------------------------------- #
    azkar_cog = bot.cogs["Azkar"]
    interaction = FakeInteraction()
    await azkar_cog.azkar.callback(azkar_cog, interaction, None)
    sent = payload(interaction)
    check("/azkar posts publicly (not ephemeral)", not sent.get("ephemeral", False))
    check("/azkar has 5 category fields", len(sent["embed"].fields) == 5)
    check("/azkar attaches persistent buttons", sent.get("view") is not None)
    check("/azkar buttons are 5", len(sent["view"].children) == 5)
    check("/azkar embed fits", len(sent["embed"]) <= 6000)

    # -- /zikr ------------------------------------------------------------ #
    interaction = FakeInteraction()
    await azkar_cog.zikr.callback(azkar_cog, interaction, None)
    sent = payload(interaction)
    check("/zikr sends a zikr", bool(sent["embed"].description))
    check("/zikr shows a source", any("المصدر" in f.name for f in sent["embed"].fields))

    # -- command tree sync payload ---------------------------------------- #
    synced_payload = []
    for cmd in bot.tree.get_commands():
        data = cmd.to_dict(bot.tree)
        synced_payload.append(data)
    names = {d["name"] for d in synced_payload}
    check("sync payload has 11 commands", len(synced_payload) == 11, str(len(synced_payload)))
    check("payload names sane", names == {
        "help", "ping", "methods", "about", "prayer", "next", "week",
        "settings", "azkar", "zikr", "azkar_reminder",
    }, str(names))
    for data in synced_payload:
        check(f"payload {data['name']} has description", bool(data.get("description")))

    # -- startup ---------------------------------------------------------- #
    check("bot has no user before login", bot.user is None)
    check("store round-trips", bot.store.get(999).city == "cairo")

    for extension in COGS:
        await bot.unload_extension(extension)
    await bot.shutdown_services()

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} failure(s)")
        for name in FAILURES:
            print(f"   - {name}")
        return 1
    print("✅ render payloads OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
