"""The bot client: shared services and small shared helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable

import discord
from discord.ext import commands

from .azkar import AzkarData
from .cities import CITIES, City, default_city, resolve
from .config import Settings, load_settings
from .health import start_background
from .prayer_times import DEFAULT_METHOD, METHODS, PrayerTimes, prayer_times_for
from .services.aladhan import AlAdhanClient
from .storage import SettingsStore

log = logging.getLogger(__name__)

COGS = (
    "salahbot.cogs.general",
    "salahbot.cogs.prayer",
    "salahbot.cogs.azkar",
)


class SalahBot(commands.Bot):
    """Discord client with the prayer/azkar services attached."""

    def __init__(self, settings: Settings | None = None) -> None:
        intents = discord.Intents.default()
        intents.message_content = False  # slash commands only: no privileged intent
        intents.guilds = True
        intents.members = False
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.settings = settings or load_settings()
        self.azkar = AzkarData()
        self.aladhan = AlAdhanClient()
        self.store = SettingsStore()
        self.started_at = datetime.now().astimezone()
        self.health = None

    # -- lifecycle -------------------------------------------------------- #
    async def setup_hook(self) -> None:
        # Some hosts insist on an HTTP health check even for worker processes;
        # start a tiny 200-OK endpoint when $PORT is provided.
        self.health = start_background()

        for extension in COGS:
            await self.load_extension(extension)
            log.info("loaded extension %s", extension)

        # Persistent components (work after a restart).
        from .ui.views import AzkarLauncherView  # local import avoids cycles

        self.add_view(AzkarLauncherView(self))

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("synced %d commands to guild %s", len(synced), guild.id)
        else:
            synced = await self.tree.sync()
            log.info("synced %d global commands", len(synced))

    async def on_ready(self) -> None:
        log.info(
            "logged in as %s (id=%s) — %d guild(s)",
            self.user,
            self.user.id if self.user else "?",
            len(self.guilds),
        )

    async def close(self) -> None:
        try:
            await self.aladhan.close()
            health = getattr(self, "health", None)
            if health is not None:
                await health.stop()
        finally:
            self.store.save()
            await super().close()

    # -- shared services -------------------------------------------------- #
    @property
    def uptime(self) -> timedelta:
        return datetime.now(self.started_at.tzinfo) - self.started_at

    def guild_defaults(self, guild_id: int | None) -> tuple[str, str]:
        """Return ``(city_key, method)`` for a guild, falling back to config."""
        if guild_id is None:
            return self.settings.default_city, DEFAULT_METHOD
        stored = self.store.get(guild_id)
        city_key = stored.city if stored.city in CITIES else self.settings.default_city
        method = stored.method if stored.method in METHODS else DEFAULT_METHOD
        return city_key, method

    async def resolve_location(self, query: str | None) -> tuple[City, bool]:
        """Resolve a city name to a :class:`City`.

        Egyptian cities are looked up locally; anything else is geocoded
        through AlAdhan.  Returns ``(city, is_local)``.
        """
        if not query:
            return default_city(), True

        local = resolve(query)
        if local is not None:
            return local, True

        remote = await self.aladhan.geocode(query)
        if remote is None:
            raise LookupError(query)

        return (
            City(
                key=f"custom:{remote['city'].lower()}",
                name_ar=remote["city"],
                name_en=remote["city"],
                latitude=remote["latitude"],
                longitude=remote["longitude"],
                timezone=remote["timezone"],
                method=DEFAULT_METHOD,
            ),
            False,
        )

    async def build_times(
        self,
        city: City | str | None,
        day: date | None = None,
        method: str | None = None,
        *,
        with_hijri: bool = True,
    ) -> tuple[PrayerTimes, str | None]:
        """Compute prayer times for a city and day (+ Hijri label)."""
        day = day or datetime.now().date()
        if isinstance(city, str):
            location, _ = await self.resolve_location(city)
        elif city is None:
            location = default_city()
        else:
            location = city

        times = prayer_times_for(
            city=location.name_ar,
            country="مصر" if location.timezone == "Africa/Cairo" else "",
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            day=day,
            method=method or location.method,
            asr_factor=location.asr,
            offsets=location.offsets,
        )
        hijri = await self.aladhan.hijri_label(times.fajr) if with_hijri else None
        return times, hijri

    async def shutdown_services(self) -> None:
        """Close the HTTP client (used by tests and scripts)."""
        await self.aladhan.close()

    # -- error reporting -------------------------------------------------- #
    async def on_app_command_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ انتظر {error.retry_after:.0f} ثانية قبل استخدام الأمر مرة أخرى.",
                ephemeral=True,
            )
            return
        log.exception("command error", exc_info=error)
        message = "حدث خطأ غير متوقع أثناء تنفيذ الأمر. حاول مرة أخرى."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"⚠️ {message}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"⚠️ {message}", ephemeral=True
                )
        except discord.HTTPException:
            pass


def city_choices() -> Iterable[tuple[str, str]]:
    """(label, key) pairs for autocomplete, ordered by Arabic name."""
    return sorted(
        ((city.name_ar, city.key) for city in CITIES.values()),
        key=lambda pair: pair[0],
    )


def method_choices() -> list[tuple[str, str]]:
    return [(f"{m.name_ar} — {m.name}", m.key) for m in METHODS.values()]
