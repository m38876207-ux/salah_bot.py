"""Azkar commands: /azkar, /zikr, /azkar_reminder."""

from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from ..ui import embeds
from ..ui.views import AzkarLauncherView, AzkarSession
from ..utils.ar import ar_number

CATEGORY_CHOICES = [
    app_commands.Choice(name="أذكار الصباح 🌅", value="morning"),
    app_commands.Choice(name="أذكار المساء 🌙", value="evening"),
    app_commands.Choice(name="بعد الصلاة 🕌", value="after_prayer"),
    app_commands.Choice(name="قبل النوم 🛏️", value="sleep"),
    app_commands.Choice(name="عند الاستيقاظ ☀️", value="wake"),
]


class Azkar(commands.Cog):
    """الأذكار — /azkar /zikr /azkar_reminder"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------ #
    # /azkar
    # ------------------------------------------------------------------ #
    @app_commands.command(
        name="azkar",
        description="أذكار الصباح والمساء وبعد الصلاة والنوم والاستيقاظ",
    )
    @app_commands.describe(category="القسم — اتركه فارغًا لعرض القائمة كاملة")
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def azkar(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ) -> None:
        data = self.bot.azkar

        if category is not None:
            chosen = data.get(category.value)
            session = AzkarSession(self.bot, interaction.user, data, chosen)
            await interaction.response.send_message(
                embed=session.render(), view=session, ephemeral=True
            )
            return

        total = sum(len(cat.items) for cat in data.ordered())
        await interaction.response.send_message(
            embed=embeds.azkar_home_embed(data.ordered(), total=total),
            view=AzkarLauncherView(self.bot),
        )

    # ------------------------------------------------------------------ #
    # /zikr
    # ------------------------------------------------------------------ #
    @app_commands.command(name="zikr", description="ذكر عشوائي من مجموعة الأذكار")
    @app_commands.describe(category="اختر قسمًا محددًا، أو اتركه عشوائيًا")
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def zikr(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ) -> None:
        data = self.bot.azkar
        if category is not None:
            chosen = data.get(category.value)
        else:
            chosen = random.choice(data.ordered())
        item = random.choice(chosen.items)

        embed = discord.Embed(
            title=f"{chosen.emoji} {chosen.name_ar}",
            description=item.text,
            color=0xC9A227,
        )
        embed.add_field(name="🔁 التكرار", value=ar_number(item.count), inline=True)
        embed.add_field(name="📖 المصدر", value=item.source or "—", inline=True)
        if item.note:
            embed.add_field(name="📝 ملاحظة", value=item.note, inline=False)
        embed.set_footer(text="استخدم /azkar لقراءة القسم كاملًا بترتيب وعدّاد")
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------ #
    # /azkar_reminder
    # ------------------------------------------------------------------ #
    @app_commands.command(
        name="azkar_reminder",
        description="عرض مواقيت تذكيرات الأذكار المفعّلة لهذا السيرفر",
    )
    async def azkar_reminder(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
            )
            return
        settings = self.bot.store.get(interaction.guild_id)
        if not settings.reminder_channel_id:
            await interaction.response.send_message(
                embed=embeds.info_embed(
                    "⏰ تذكيرات الأذكار غير مفعّلة",
                    "استخدم `/settings reminders channel:#القناة` لتفعيل "
                    "تذكير أذكار الصباح بعد الفجر وأذكار المساء بعد المغرب.",
                ),
                ephemeral=True,
            )
            return

        city_name = settings.city
        embed = embeds.info_embed(
            "⏰ تذكيرات الأذكار",
            f"القناة: <#{settings.reminder_channel_id}>\n"
            f"🌅 أذكار الصباح: {'مفعّلة ✅ بعد الفجر' if settings.morning_reminder else 'موقوفة ⛔'}\n"
            f"🌙 أذكار المساء: {'مفعّلة ✅ بعد المغرب' if settings.evening_reminder else 'موقوفة ⛔'}\n\n"
            "غيّر الإعدادات بأمر `/settings reminders`.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Azkar(bot))
