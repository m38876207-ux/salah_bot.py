"""Per-guild settings, persisted to a small JSON file."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import SETTINGS_FILE

log = logging.getLogger(__name__)


@dataclass
class GuildSettings:
    city: str = "cairo"
    method: str = "egypt"
    reminder_channel_id: int | None = None
    morning_reminder: bool = False
    evening_reminder: bool = False
    # last date we sent each reminder, "YYYY-MM-DD", to avoid duplicates
    last_morning: str = ""
    last_evening: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SettingsStore:
    """Thread-safe JSON-backed store keyed by guild id."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SETTINGS_FILE
        self._lock = threading.RLock()
        self._data: dict[int, GuildSettings] = {}
        self.load()

    # -- persistence ------------------------------------------------------ #
    def load(self) -> None:
        with self._lock:
            if not self.path.is_file():
                self._data = {}
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("could not read %s: %s", self.path, exc)
                self._data = {}
                return
            parsed: dict[int, GuildSettings] = {}
            for key, value in (raw.get("guilds") or {}).items():
                try:
                    parsed[int(key)] = GuildSettings(
                        **{
                            name: value[name]
                            for name in GuildSettings.__dataclass_fields__
                            if name in value
                        }
                    )
                except (TypeError, ValueError):
                    log.warning("skipping malformed guild settings for %s", key)
            self._data = parsed

    def save(self) -> None:
        with self._lock:
            payload = {
                "guilds": {
                    str(gid): settings.to_dict()
                    for gid, settings in self._data.items()
                }
            }
            try:
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                tmp.replace(self.path)
            except OSError as exc:
                log.warning("could not save %s: %s", self.path, exc)

    # -- access ----------------------------------------------------------- #
    def get(self, guild_id: int | None) -> GuildSettings:
        if guild_id is None:
            return GuildSettings()
        with self._lock:
            return self._data.setdefault(guild_id, GuildSettings())

    def update(self, guild_id: int | None, **changes) -> GuildSettings:
        if guild_id is None:
            raise ValueError("guild settings require a guild")
        with self._lock:
            settings = self._data.setdefault(guild_id, GuildSettings())
            for name, value in changes.items():
                if not hasattr(settings, name):
                    raise AttributeError(name)
                setattr(settings, name, value)
            self.save()
            return settings

    def all_guilds(self) -> dict[int, GuildSettings]:
        with self._lock:
            return dict(self._data)
