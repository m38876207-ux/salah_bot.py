"""Configuration and shared constants."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SETTINGS_FILE = PROJECT_DIR / "guild_settings.json"

# Fallback .env loader (keeps dependencies at zero beyond discord.py).
_ENV_FILE = PROJECT_DIR / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv(_ENV_FILE)

# --------------------------------------------------------------------------- #
# Branding
# --------------------------------------------------------------------------- #

COLOR_GREEN = 0x1F8B4C
COLOR_GOLD = 0xC9A227
COLOR_RED = 0xB3261E
COLOR_BLUE = 0x2F6FED
ACCENT = COLOR_GREEN

EMOJI = {
    "fajr": "🌌",
    "sunrise": "🌅",
    "dhuhr": "☀️",
    "asr": "🌤️",
    "maghrib": "🌇",
    "isha": "🌙",
}

ARABIC_LABELS = {
    "fajr": ("الفجر", "Fajr"),
    "sunrise": ("الشروق", "Sunrise"),
    "dhuhr": ("الظهر", "Dhuhr"),
    "asr": ("العصر", "Asr"),
    "maghrib": ("المغرب", "Maghrib"),
    "isha": ("العشاء", "Isha"),
}

# Short lines shown under /help and in the empty-state embeds.
TAGLINE = "مواقيت الصلاة في مصر وأذكار الصباح والمساء"


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None = None
    default_city: str = "cairo"
    owner_ids: tuple[int, ...] = field(default_factory=tuple)
    log_level: str = "INFO"

    @property
    def is_configured(self) -> bool:
        return bool(self.token)


def load_settings() -> Settings:
    token = (os.environ.get("DISCORD_TOKEN") or "").strip()
    guild_raw = (os.environ.get("DISCORD_GUILD_ID") or "").strip()
    guild_id: int | None = None
    if guild_raw.isdigit():
        guild_id = int(guild_raw)

    owners_raw = (os.environ.get("OWNER_IDS") or "").strip()
    owners: tuple[int, ...] = tuple(
        int(part) for part in owners_raw.replace(";", ",").split(",") if part.strip().isdigit()
    )

    return Settings(
        token=token,
        guild_id=guild_id,
        default_city=(os.environ.get("DEFAULT_CITY") or "cairo").strip().lower(),
        owner_ids=owners,
        log_level=(os.environ.get("LOG_LEVEL") or "INFO").upper(),
    )
