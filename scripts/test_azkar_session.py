"""
Interaction-level test for the azkar session state machine.

Discord's HTTP layer is faked, so this exercises the view logic (counter
limits, navigation, category switching, completion) without a token.

    python scripts/test_azkar_session.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord  # noqa: E402

from salahbot.azkar import AzkarData  # noqa: E402
from salahbot.bot import SalahBot  # noqa: E402
from salahbot.config import Settings  # noqa: E402
from salahbot.ui.views import AzkarLauncherView, AzkarSession  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


class FakeResponse:
    def __init__(self) -> None:
        self.edits: list[dict] = []
        self.sent: list[dict] = []
        self.deferred = False

    async def edit_message(self, **kwargs) -> None:
        self.edits.append(kwargs)

    async def send_message(self, *args, **kwargs) -> None:
        self.sent.append(kwargs)

    async def defer(self) -> None:
        self.deferred = True

    def is_done(self) -> bool:
        return bool(self.edits or self.sent)


def fake_interaction(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id, display_name="Tester"),
        response=FakeResponse(),
    )


async def main() -> int:
    bot = SalahBot(Settings(token="dummy"))
    data = AzkarData()
    author = SimpleNamespace(id=1, display_name="Tester")

    # -- construction ---------------------------------------------------- #
    session = AzkarSession(bot, author, data, data.get("morning"))
    check("session has 6 components", len(session.children) == 6, str(len(session.children)))
    check("starts at item 0", session.index == 0)
    check("counter starts at 0", session.count == 0)
    check("prev disabled at start", session.prev_button.disabled)
    check("next enabled", not session.next_button.disabled)
    check("embed renders", "أذكار الصباح" in (session.render().title or ""))

    # -- counter --------------------------------------------------------- #
    item = session.item
    for _ in range(item.count):
        await session._on_counter(fake_interaction())
    check(f"counter caps at {item.count}", session.count == item.count, str(session.count))
    check("counter button disabled when done", session.counter_button.disabled)
    check("counter label says done", "تم" in session.counter_button.label)
    check("progress embed marks done", "✅" in session.render().fields[0].value)

    # extra clicks cannot exceed the target
    await session._on_counter(fake_interaction())
    check("counter cannot exceed target", session.count == item.count)

    # -- navigation ------------------------------------------------------ #
    await session._on_next(fake_interaction())
    check("next moves to item 1", session.index == 1, str(session.index))
    check("counter reset on move", session.count == 0)
    check("prev enabled on item 1", not session.prev_button.disabled)
    await session._on_prev(fake_interaction())
    check("prev returns to item 0", session.index == 0)

    # -- category switch -------------------------------------------------- #
    session.switch_category  # exists
    await session.switch_category("sleep", fake_interaction())
    select = next(c for c in session.children if isinstance(c, discord.ui.Select))
    check("category switched", session.category.key == "sleep", session.category.key)
    check("index reset on category switch", session.index == 0)
    check("select options cover 5 categories", len(select.options) == 5)

    # -- finishing the last item ------------------------------------------ #
    await session._on_restart(fake_interaction())
    last = len(session.category.items) - 1
    while session.index < last:
        await session._on_next(fake_interaction())
    check("reached last item", session.index == last)
    interaction = fake_interaction()
    await session._on_next(interaction)
    check("view stopped at end", session.is_finished())
    check("completion embed sent", "أنهيت" in (interaction.response.edits[-1]["embed"].title or ""))

    # -- author check ----------------------------------------------------- #
    session2 = AzkarSession(bot, author, data, data.get("evening"))
    allowed = await session2.interaction_check(fake_interaction(user_id=99))
    check("other users are rejected", allowed is False)

    # -- launcher --------------------------------------------------------- #
    launcher = AzkarLauncherView(bot)
    interaction = fake_interaction()
    result = await launcher._open(interaction, "morning")
    check("launcher opens ephemeral session", interaction.response.sent and interaction.response.sent[0].get("ephemeral") is True)
    check("launcher sends a session view", isinstance(interaction.response.sent[0].get("view"), AzkarSession))

    await bot.shutdown_services()

    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} failure(s)")
        return 1
    print("✅ azkar session logic OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
