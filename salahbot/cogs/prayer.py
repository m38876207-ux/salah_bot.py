"""Prayer-time commands and reminder loop."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..cities import CITIES, default_city
from ..prayer_times import METHODS
from ..ui import embeds
from ..ui.views import PrayerView

log = logging.getLogger(__name__)

DATE_CHOICES = [
    app_commands.Choice(name="اليوم", value="today"),
    app_commands.Choice(name="غدًا", value="tomorrow"),
]

WEEK = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


async def _autocomplete_city(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Fuzzy-ish city autocomplete: exact and prefix matches first."""
    needle = (current or "").strip().lower()
    scored: list[tuple[int, str, app_commands.Choice[str]]] = []
    for city in CITIES.values():
        ar_lower = city.name_ar.lower()
        en_key = city.key
        en_lower = city.name_en.lower()
        if not needle:
            rank = 0
        elif ar_lower == needle or en_lower == needle or en_key == needle:
            rank = 3
        elif (
            ar_lower.startswith(needle)
            or en_lower.startswith(needle)
            or en_key.startswith(needle)
        ):
            rank = 2
        elif needle in ar_lower or needle in en_lower or needle in en_key:
            rank = 1
        else:
            continue
        scored.append(
            (rank, city.name_ar, app_commands.Choice(name=city.label, value=city.name_ar))
        )
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:25]]


class Prayer(commands.Cog):
    """مواقيت الصلاة — /prayer /next /week /settings"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # The loop's before_loop hook waits for readiness, so starting it
        # before login is safe; guard against a double start on reload.
        if not self.reminder_loop.is_running():
            self.reminder_loop.start()

    async def cog_unload(self) -> None:
        self.reminder_loop.cancel()

    # ------------------------------------------------------------------ #
    # /prayer
    # ------------------------------------------------------------------ #
    @app_commands.command(
        name="prayer",
        description="مواقيت الصلاة لليوم في أي مدينة مصرية (أو أي مدينة في العالم)",
    )
    @app_commands.describe(
        city="المدينة — القاهرة افتراضيًا",
        day="اليوم أو غدًا",
        method="طريقة الحساب (الهيئة المصرية افتراضيًا)",
    )
    @app_commands.choices(day=DATE_CHOICES)
    @app_commands.autocomplete(city=_autocomplete_city)
    async def prayer(
        self,
        interaction: discord.Interaction,
        city: str | None = None,
        day: app_commands.Choice[str] | None = None,
        method: str | None = None,
    ) -> None:
        await interaction.response.defer()

        guild_city, guild_method = self.bot.guild_defaults(
            interaction.guild_id if interaction.guild else None
        )
        query = city or CITIES[guild_city].name_ar
        method_key = method if method in METHODS else guild_method
        target_day = date.today() + (
            timedelta(days=1) if day is not None and day.value == "tomorrow" else timedelta(0)
        )

        try:
            location, _ = await self.bot.resolve_location(query)
        except LookupError:
            await interaction.followup.send(
                embed=embeds.error_embed(
                    "لم أجد هذه المدينة. جرّب اسمًا مصريًا من القائمة، "
                    "أو اسم مدينة باللغة الإنجليزية.",
                    title="مدينة غير معروفة",
                )
            )
            return

        times, hijri = await self.bot.build_times(location, target_day, method_key)
        view = PrayerView(
            self.bot,
            city_key=(
                location.key if location.key in CITIES else location.name_ar
            ),
            day=target_day,
            method=method_key,
            author=interaction.user,
        )
        view._sync_buttons()
        await interaction.followup.send(
            embed=embeds.prayer_embed(
                times,
                hijri=hijri,
                title_suffix=" — غدًا" if target_day > date.today() else "",
            ),
            view=view,
        )

    # ------------------------------------------------------------------ #
    # /next
    # ------------------------------------------------------------------ #
    @app_commands.command(
        name="next", description="الصلاة القادمة والوقت المتبقي لها"
    )
    @app_commands.describe(city="المدينة — القاهرة افتراضيًا")
    @app_commands.autocomplete(city=_autocomplete_city)
    async def next_prayer(
        self, interaction: discord.Interaction, city: str | None = None
    ) -> None:
        await interaction.response.defer()
        guild_city, guild_method = self.bot.guild_defaults(
            interaction.guild_id if interaction.guild else None
        )
        query = city or CITIES[guild_city].name_ar
        try:
            location, _ = await self.bot.resolve_location(query)
        except LookupError:
            await interaction.followup.send(
                embed=embeds.error_embed("لم أجد هذه المدينة.", title="مدينة غير معروفة")
            )
            return

        now = datetime.now().astimezone()
        local_now = now.astimezone(ZoneInfo(location.timezone))
        times, _ = await self.bot.build_times(
            location, local_now.date(), guild_method, with_hijri=False
        )
        upcoming = times.next_prayer(local_now)
        if upcoming is None:
            tomorrow_day = local_now.date() + timedelta(days=1)
            tomorrow, _ = await self.bot.build_times(
                location, tomorrow_day, guild_method, with_hijri=False
            )
            await interaction.followup.send(
                embed=embeds.next_prayer_embed(
                    tomorrow,
                    ("fajr", tomorrow.fajr),
                    now=local_now,
                )
            )
            return

        await interaction.followup.send(
            embed=embeds.next_prayer_embed(times, upcoming, now=local_now)
        )

    # ------------------------------------------------------------------ #
    # /week
    # ------------------------------------------------------------------ #
    @app_commands.command(name="week", description="جدول مواقيت الأسبوع")
    @app_commands.describe(city="المدينة — القاهرة افتراضيًا", method="طريقة الحساب")
    @app_commands.autocomplete(city=_autocomplete_city)
    async def week(
        self,
        interaction: discord.Interaction,
        city: str | None = None,
        method: str | None = None,
    ) -> None:
        await interaction.response.defer()
        guild_city, guild_method = self.bot.guild_defaults(
            interaction.guild_id if interaction.guild else None
        )
        try:
            location, _ = await self.bot.resolve_location(
                city or CITIES[guild_city].name_ar
            )
        except LookupError:
            await interaction.followup.send(
                embed=embeds.error_embed("لم أجد هذه المدينة.", title="مدينة غير معروفة")
            )
            return
        method_key = method if method in METHODS else guild_method

        start = date.today()
        rows = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            times, _ = await self.bot.build_times(
                location, day, method_key, with_hijri=False
            )
            rows.append((day, times))
        embed = embeds.week_embed(rows)
        embed.title = f"📅 مواقيت الأسبوع — {location.name_ar}"
        await interaction.followup.send(embed=embed)

    # ------------------------------------------------------------------ #
    # /settings
    # ------------------------------------------------------------------ #
    settings_group = app_commands.Group(
        name="settings", description="إعدادات السيرفر: المدينة والطريقة والتذكيرات"
    )

    @settings_group.command(name="city", description="تحديد المدينة الافتراضية للسيرفر")
    @app_commands.describe(city="المدينة المصرية")
    @app_commands.autocomplete(city=_autocomplete_city)
    async def settings_city(
        self, interaction: discord.Interaction, city: str
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
            )
            return
        location, is_local = await self.bot.resolve_location(city)
        if not is_local:
            await interaction.response.send_message(
                embed=embeds.error_embed(
                    "الإعداد الافتراضي يدعم المدن المصرية فقط. "
                    "يمكنك تمرير أي مدينة عالمية مباشرة للأمر `/prayer city:`"
                ),
                ephemeral=True,
            )
            return
        self.bot.store.update(interaction.guild_id, city=location.key)
        await interaction.response.send_message(
            embed=embeds.info_embed(
                "✅ تم تحديث المدينة",
                f"المدينة الافتراضية الآن: **{location.label}**",
            ),
            ephemeral=True,
        )

    @settings_group.command(name="method", description="تحديد طريقة حساب المواقيت")
    @app_commands.describe(method="طريقة الحساب")
    @app_commands.choices(
        method=[
            app_commands.Choice(name=f"{m.name_ar} — {m.name}", value=m.key)
            for m in METHODS.values()
        ]
    )
    async def settings_method(
        self, interaction: discord.Interaction, method: app_commands.Choice[str]
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
            )
            return
        definition = METHODS[method.value]
        self.bot.store.update(interaction.guild_id, method=definition.key)
        await interaction.response.send_message(
            embed=embeds.info_embed(
                "✅ تم تحديث طريقة الحساب",
                f"الطريقة الحالية: **{definition.name_ar}** ({definition.name})",
            ),
            ephemeral=True,
        )

    @settings_group.command(
        name="reminders", description="تفعيل أو إيقاف تذكير أذكار الصباح والمساء"
    )
    @app_commands.describe(
        channel="القناة التي تُرسل فيها التذكيرات",
        morning="تذكير أذكار الصباح بعد الفجر",
        evening="تذكير أذكار المساء بعد المغرب",
    )
    async def settings_reminders(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        morning: bool = True,
        evening: bool = True,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
            )
            return
        me = interaction.guild.me
        if me is not None:
            perms = channel.permissions_for(me)
            if not (perms.send_messages and perms.embed_links):
                await interaction.response.send_message(
                    embed=embeds.error_embed(
                        f"ليست لدي صلاحية الإرسال أو تضمين الروابط في {channel.mention}.",
                        title="صلاحيات ناقصة",
                    ),
                    ephemeral=True,
                )
                return
        self.bot.store.update(
            interaction.guild_id,
            reminder_channel_id=channel.id,
            morning_reminder=morning,
            evening_reminder=evening,
        )
        await interaction.response.send_message(
            embed=embeds.info_embed(
                "✅ تم تحديث التذكيرات",
                f"القناة: {channel.mention}\n"
                f"أذكار الصباح: {'مفعّلة ✅' if morning else 'موقوفة ⛔'}\n"
                f"أذكار المساء: {'مفعّلة ✅' if evening else 'موقوفة ⛔'}\n\n"
                "يُرسل التذكير بعد صلاة الفجر وبعد المغرب بتوقيت القاهرة.",
            ),
            ephemeral=True,
        )

    @settings_group.command(name="show", description="عرض إعدادات السيرفر الحالية")
    async def settings_show(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "هذا الأمر يعمل داخل السيرفرات فقط.", ephemeral=True
            )
            return
        settings = self.bot.store.get(interaction.guild_id)
        city = CITIES.get(settings.city) or default_city()
        method = METHODS.get(settings.method)
        channel = (
            f"<#{settings.reminder_channel_id}>"
            if settings.reminder_channel_id
            else "—"
        )
        await interaction.response.send_message(
            embed=embeds.info_embed(
                "⚙️ إعدادات السيرفر",
                f"📍 المدينة: **{city.label}**\n"
                f"🧮 الطريقة: **{method.name_ar if method else settings.method}**\n"
                f"📣 قناة التذكيرات: {channel}\n"
                f"🌅 تذكير الصباح: {'مفعّل ✅' if settings.morning_reminder else 'متوقف ⛔'}\n"
                f"🌙 تذكير المساء: {'مفعّل ✅' if settings.evening_reminder else 'متوقف ⛔'}",
            ),
            ephemeral=True,
        )

    # ------------------------------------------------------------------ #
    # Reminder loop
    # ------------------------------------------------------------------ #
    @tasks.loop(seconds=30)
    async def reminder_loop(self) -> None:
        """Send morning/evening adhkar reminders shortly after Fajr/Maghrib."""
        now = datetime.now().astimezone()
        today_key = now.date().isoformat()

        for guild_id, settings in self.bot.store.all_guilds().items():
            if not settings.reminder_channel_id:
                continue

            city = CITIES.get(settings.city) or default_city()
            local_now = now.astimezone(_tz(city.timezone))
            times, _ = await self.bot.build_times(
                city, local_now.date(), settings.method, with_hijri=False
            )

            for label, enabled, anchor, attr in (
                ("أذكار الصباح", settings.morning_reminder, times.fajr, "last_morning"),
                ("أذكار المساء", settings.evening_reminder, times.maghrib, "last_evening"),
            ):
                if not enabled or getattr(settings, attr) == today_key:
                    continue
                elapsed = (local_now - anchor).total_seconds()
                if not (0 <= elapsed <= 2 * 3600):
                    continue

                channel = self.bot.get_channel(settings.reminder_channel_id)
                if channel is None:
                    continue
                category = self.bot.azkar.get(
                    "morning" if "الصباح" in label else "evening"
                )
                try:
                    embed = embeds.azkar_reminder_embed(category, label=label)
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    log.warning("failed to send reminder to guild %s", guild_id)
                    continue
                self.bot.store.update(guild_id, **{attr: today_key})

    @reminder_loop.before_loop
    async def _before_reminder_loop(self) -> None:
        try:
            await self.bot.wait_until_ready()
        except RuntimeError:
            # The client was never logged in (tests, dry runs).  Bail out
            # quietly instead of leaving an unhandled task exception behind.
            log.debug("reminder loop skipped: client not initialised")
            return

    @reminder_loop.error
    async def _reminder_error(self, error: BaseException) -> None:
        log.exception("reminder loop crashed", exc_info=error)


def _tz(name: str) -> ZoneInfo:
    return ZoneInfo(name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Prayer(bot))
