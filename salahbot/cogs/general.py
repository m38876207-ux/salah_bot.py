"""General information commands: /help, /ping, /methods, /about."""

from __future__ import annotations

import platform

import discord
from discord import app_commands
from discord.ext import commands

from .. import __version__
from ..prayer_times import DEFAULT_METHOD, METHODS
from ..ui import embeds
from ..utils.ar import ar_number


class General(commands.Cog):
    """Info and utility commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="قائمة الأوامر وطريقة الاستخدام")
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=embeds.help_embed(), ephemeral=True
        )

    @app_commands.command(name="ping", description="سرعة استجابة البوت")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            embed=embeds.info_embed(
                "🏓 بونج!",
                f"زمن الاستجابة: **{ar_number(latency)} مللي ثانية**\n"
                f"متصل بأمان بـ {ar_number(len(self.bot.guilds))} سيرفر",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="methods", description="طرق حساب المواقيت المتاحة")
    async def methods(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🧮 طرق حساب المواقيت",
            description=(
                "الطريقة الافتراضية **الهيئة المصرية العامة للمساحة** "
                "(الفجر ١٩.٥°، العشاء ١٧.٥°، مذهب الشافعي).\n"
                "يمكن تغييرها بأمر `/settings method` أو مباشرة مع `/prayer method:`"
            ),
            color=0x2F6FED,
        )
        for method in METHODS.values():
            fajr = f"{method.fajr_angle:g}°"
            if method.isha_angle is not None:
                isha = f"{method.isha_angle:g}°"
            else:
                isha = f"بعد المغرب {method.isha_interval:g} دقيقة"
            marker = " ⭐" if method.key == DEFAULT_METHOD else ""
            embed.add_field(
                name=f"{method.name_ar} — {method.name}{marker}",
                value=f"`{method.key}` · الفجر {fajr} · العشاء {isha}",
                inline=False,
            )
        embed.set_footer(text="⭐ = الطريقة الافتراضية للبوت")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="عن البوت")
    async def about(self, interaction: discord.Interaction) -> None:
        uptime = self.bot.uptime
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes = rem // 60
        embed = discord.Embed(
            title="🕌 بوت مواقيت الصلاة والأذكار",
            description=(
                "مواقيت الصلاة لجميع مدن مصر + أذكار الصباح والمساء "
                "وأذكار بعد الصلاة والنوم والاستيقاظ.\n"
                "المواقيت تُحسب محليًا بنفس الخوارزمية الفلكية للهيئة المصرية."
            ),
            color=0x1F8B4C,
        )
        embed.add_field(
            name="الإصدار",
            value=f"`{__version__}` · Python `{platform.python_version()}` · discord.py `{discord.__version__}`",
            inline=False,
        )
        embed.add_field(
            name="مدة التشغيل",
            value=f"{ar_number(hours)} س {ar_number(minutes)} د",
            inline=True,
        )
        embed.add_field(
            name="السيرفرات", value=ar_number(len(self.bot.guilds)), inline=True
        )
        embed.add_field(
            name="طلبات الأذكار",
            value=ar_number(len(self.bot.azkar.ordered())),
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
