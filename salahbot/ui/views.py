"""Interactive views: azkar browser, prayer-time navigator, persistent launcher."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

import discord

from ..azkar import AzkarData, Category
from ..ui import embeds
from ..utils.ar import ar_number

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..bot import SalahBot

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Azkar
# --------------------------------------------------------------------------- #


class AzkarSession(discord.ui.View):
    """A per-user azkar reading session with a repetition counter.

    Holds personal progress in memory and is posted ephemerally, so the
    persistent entry point stays :class:`AzkarLauncherView`.
    """

    def __init__(
        self,
        bot: "SalahBot",
        author: discord.abc.User,
        data: AzkarData,
        category: Category,
    ) -> None:
        super().__init__(timeout=900)
        self.bot = bot
        self.author = author
        self.data = data
        self.category = category
        self.index = 0
        self.count = 0
        self._build()

    # -- state helpers ---------------------------------------------------- #
    @property
    def item(self):
        return self.category.items[self.index]

    def _build(self) -> None:
        """Recreate all components so enabled/disabled state stays correct."""
        self.clear_items()

        self.counter_button = discord.ui.Button(
            label="سُبْحَانَ اللَّهِ",
            style=discord.ButtonStyle.primary,
            row=0,
        )
        self.counter_button.callback = self._on_counter
        self.add_item(self.counter_button)

        self.prev_button = discord.ui.Button(
            label="▶ السابق", style=discord.ButtonStyle.secondary, row=1
        )
        self.prev_button.callback = self._on_prev
        self.add_item(self.prev_button)

        self.next_button = discord.ui.Button(
            label="التالي ◀", style=discord.ButtonStyle.success, row=1
        )
        self.next_button.callback = self._on_next
        self.add_item(self.next_button)

        self.restart_button = discord.ui.Button(
            label="🔄 من الأول", style=discord.ButtonStyle.secondary, row=2
        )
        self.restart_button.callback = self._on_restart
        self.add_item(self.restart_button)

        self.close_button = discord.ui.Button(
            label="✖ إغلاق", style=discord.ButtonStyle.danger, row=2
        )
        self.close_button.callback = self._on_close
        self.add_item(self.close_button)

        select = discord.ui.Select(
            placeholder=f"📿 القسم الحالي: {self.category.name_ar}",
            options=[
                discord.SelectOption(
                    label=f"{cat.name_ar} ({ar_number(len(cat.items))})",
                    value=cat.key,
                    emoji=cat.emoji,
                    description=cat.name_en,
                    default=cat.key == self.category.key,
                )
                for cat in self.data.ordered()[:25]
            ],
            row=3,
        )
        select.callback = self._on_category
        self.add_item(select)

        self._sync()

    def _sync(self) -> None:
        done = self.count >= self.item.count
        self.prev_button.disabled = self.index == 0
        self.next_button.disabled = self.index >= len(self.category.items) - 1
        self.counter_button.disabled = done
        if done:
            self.counter_button.label = "✅ تم"
            self.counter_button.style = discord.ButtonStyle.success
        else:
            self.counter_button.label = f"سُبْحَانَ اللَّهِ ({ar_number(self.item.count)})"
            self.counter_button.style = discord.ButtonStyle.primary

    def render(self) -> discord.Embed:
        return embeds.azkar_item_embed(
            self.category,
            self.index,
            self.count,
            viewer=self.author.display_name,
        )

    async def _update(self, interaction: discord.Interaction) -> None:
        self._sync()
        await interaction.response.edit_message(embed=self.render(), view=self)

    # -- checks ----------------------------------------------------------- #
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "هذه الجلسة ليست لك — استخدم `/azkar` لعمل جلسة خاصة بك.",
                ephemeral=True,
            )
            return False
        return True

    # -- callbacks -------------------------------------------------------- #
    async def _on_counter(self, interaction: discord.Interaction) -> None:
        self.count = min(self.count + 1, self.item.count)
        await self._update(interaction)

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        if self.index > 0:
            self.index -= 1
            self.count = 0
        await self._update(interaction)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        if self.index < len(self.category.items) - 1:
            self.index += 1
            self.count = 0
            await self._update(interaction)
            return
        # Last item finished: celebrate and retire the view.
        self.stop()
        await interaction.response.edit_message(
            embed=embeds.azkar_finished_embed(self.category), view=None
        )

    async def _on_restart(self, interaction: discord.Interaction) -> None:
        self.index = 0
        self.count = 0
        self._build()
        await interaction.response.edit_message(embed=self.render(), view=self)

    async def _on_close(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.edit_message(
            embed=embeds.info_embed(
                "أُغلقت الجلسة",
                "تقبّل الله منك 🤲 — استخدم `/azkar` في أي وقت لفتح جلسة جديدة.",
            ),
            view=None,
        )

    async def _on_category(self, interaction: discord.Interaction) -> None:
        select = next(
            child for child in self.children if isinstance(child, discord.ui.Select)
        )
        if not select.values:
            await interaction.response.defer()
            return
        await self.switch_category(select.values[0], interaction)

    async def switch_category(
        self, key: str, interaction: discord.Interaction | None = None
    ) -> None:
        self.category = self.data.get(key)
        self.index = 0
        self.count = 0
        self._build()
        if interaction is not None:
            await interaction.response.edit_message(embed=self.render(), view=self)

    async def on_timeout(self) -> None:
        log.debug("azkar session for %s timed out", self.author.id)


class AzkarLauncherView(discord.ui.View):
    """Persistent buttons attached to the /azkar post.

    Registered with ``bot.add_view`` so they keep working after a restart.
    Each click opens a fresh private session for that user.
    """

    def __init__(self, bot: "SalahBot") -> None:
        super().__init__(timeout=None)
        self.bot = bot

    async def _open(self, interaction: discord.Interaction, key: str) -> None:
        data: AzkarData = self.bot.azkar
        session = AzkarSession(self.bot, interaction.user, data, data.get(key))
        await interaction.response.send_message(
            embed=session.render(), view=session, ephemeral=True
        )

    @discord.ui.button(
        label="🌅 الصباح",
        style=discord.ButtonStyle.primary,
        custom_id="azkar:open:morning",
    )
    async def morning(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._open(interaction, "morning")

    @discord.ui.button(
        label="🌙 المساء",
        style=discord.ButtonStyle.primary,
        custom_id="azkar:open:evening",
    )
    async def evening(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._open(interaction, "evening")

    @discord.ui.button(
        label="🕌 بعد الصلاة",
        style=discord.ButtonStyle.secondary,
        custom_id="azkar:open:after_prayer",
    )
    async def after_prayer(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._open(interaction, "after_prayer")

    @discord.ui.button(
        label="🛏️ النوم",
        style=discord.ButtonStyle.secondary,
        custom_id="azkar:open:sleep",
    )
    async def sleep(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._open(interaction, "sleep")

    @discord.ui.button(
        label="☀️ الاستيقاظ",
        style=discord.ButtonStyle.secondary,
        custom_id="azkar:open:wake",
    )
    async def wake(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._open(interaction, "wake")


# --------------------------------------------------------------------------- #
# Prayer times
# --------------------------------------------------------------------------- #


class PrayerView(discord.ui.View):
    """Day navigation for /prayer: previous, refresh, next."""

    def __init__(
        self,
        bot: "SalahBot",
        *,
        city_key: str,
        day: date,
        method: str,
        author: discord.abc.User,
        timeout: int = 600,
    ) -> None:
        super().__init__(timeout=timeout)
        self.bot = bot
        self.city_key = city_key
        self.day = day
        self.method = method
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "استخدم `/prayer` لمتابعة مواقيتك بنفسك.", ephemeral=True
            )
            return False
        return True

    async def _render(self) -> None:
        times, hijri = await self.bot.build_times(self.city_key, self.day, self.method)
        self._sync_buttons()
        return embeds.prayer_embed(times, hijri=hijri)

    def _sync_buttons(self) -> None:
        today = date.today()
        self.prev_button.disabled = self.day <= today - timedelta(days=7)
        self.next_button.disabled = self.day >= today + timedelta(days=30)

    @discord.ui.button(label="◀ اليوم السابق", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.day -= timedelta(days=1)
        await interaction.response.edit_message(
            embed=await self._render(), view=self
        )

    @discord.ui.button(label="🔄 تحديث", style=discord.ButtonStyle.primary)
    async def refresh_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(
            embed=await self._render(), view=self
        )

    @discord.ui.button(label="اليوم التالي ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.day += timedelta(days=1)
        await interaction.response.edit_message(
            embed=await self._render(), view=self
        )
