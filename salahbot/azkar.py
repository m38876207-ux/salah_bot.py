"""Azkar data model and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import DATA_DIR


@dataclass(frozen=True)
class Zikr:
    id: str
    text: str
    count: int
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class Category:
    key: str
    name_ar: str
    name_en: str
    emoji: str
    description_ar: str
    items: tuple[Zikr, ...]

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.name_ar}"

    @property
    def total_repetitions(self) -> int:
        return sum(item.count for item in self.items)


class AzkarData:
    """Loads ``data/azkar.json`` and exposes it in a convenient shape."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_DIR / "azkar.json"
        self.categories: dict[str, Category] = {}
        self._order: list[str] = []
        self.load()

    def load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        categories = raw.get("categories", [])
        if not categories:
            raise ValueError(f"no categories found in {self.path}")

        parsed: dict[str, Category] = {}
        for entry in categories:
            key = str(entry["key"])
            items = tuple(
                Zikr(
                    id=str(item.get("id") or f"{key}-{index}"),
                    text=str(item["text"]).strip(),
                    count=max(1, int(item.get("count", 1))),
                    source=str(item.get("source") or "").strip(),
                    note=str(item.get("note") or "").strip(),
                )
                for index, item in enumerate(entry.get("items", []), start=1)
            )
            if not items:
                continue
            parsed[key] = Category(
                key=key,
                name_ar=str(entry.get("name_ar") or key),
                name_en=str(entry.get("name_en") or key),
                emoji=str(entry.get("emoji") or "📿"),
                description_ar=str(entry.get("description_ar") or ""),
                items=items,
            )
        self.categories = parsed
        self._order = [str(entry["key"]) for entry in categories if str(entry["key"]) in parsed]

    # -- access ----------------------------------------------------------- #
    @property
    def keys(self) -> list[str]:
        return list(self._order)

    def get(self, key: str) -> Category:
        try:
            return self.categories[key]
        except KeyError:
            raise KeyError(f"unknown azkar category: {key!r}") from None

    def ordered(self) -> list[Category]:
        return [self.categories[key] for key in self._order]

    # -- quick validation used by tests ---------------------------------- #
    def validate(self) -> list[str]:
        problems: list[str] = []
        seen: set[str] = set()
        for category in self.ordered():
            if not category.items:
                problems.append(f"{category.key}: no items")
            for item in category.items:
                if item.id in seen:
                    problems.append(f"duplicate id {item.id}")
                seen.add(item.id)
                if not item.text:
                    problems.append(f"{item.id}: empty text")
                if item.count < 1:
                    problems.append(f"{item.id}: bad count {item.count}")
        return problems
