"""
Offline smoke test — verifies the whole project without a Discord token.

    python scripts/smoke_test.py

Checks: package imports, azkar data integrity, prayer-time calculation,
embed rendering, view construction, and the CLI --check path.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


def main() -> int:
    # ------------------------------------------------------------------ #
    print("== imports ==")
    from salahbot import __version__
    from salahbot.azkar import AzkarData
    from salahbot.bot import COGS
    from salahbot.cities import CITIES, resolve
    from salahbot.prayer_times import METHODS, calculate_times, prayer_times_for
    from salahbot.ui import embeds
    from salahbot.ui.views import AzkarLauncherView, PrayerView
    from salahbot.utils import ar

    check("version is a string", isinstance(__version__, str))
    check("cogs registered", len(COGS) == 3, str(COGS))

    # ------------------------------------------------------------------ #
    print("\n== azkar data ==")
    data = AzkarData()
    problems = data.validate()
    check("data validates", not problems, "; ".join(problems[:3]))
    check("5 categories", len(data.ordered()) == 5, str(data.keys))
    total = sum(len(c.items) for c in data.ordered())
    check("items loaded", total >= 40, f"{total} items")
    for key in ("morning", "evening", "after_prayer", "sleep", "wake"):
        check(f"category {key}", key in data.categories)

    # ------------------------------------------------------------------ #
    print("\n== city lookup ==")
    check("cities loaded", len(CITIES) >= 35, f"{len(CITIES)} cities")
    for query in ("Cairo", "القاهرة", "alex", "الإسكندرية", "6 October", "sharm"):
        check(f"resolve {query!r}", resolve(query) is not None)
    check("unknown city -> None", resolve("atlantis-but-not-really") is None)

    # ------------------------------------------------------------------ #
    print("\n== prayer times ==")
    cairo = CITIES["cairo"]
    times = prayer_times_for(
        city=cairo.name_ar,
        country="مصر",
        latitude=cairo.latitude,
        longitude=cairo.longitude,
        timezone=cairo.timezone,
        day=date(2026, 11, 14),
    )
    expected = {
        "fajr": "04:49",
        "sunrise": "06:19",
        "dhuhr": "11:39",
        "asr": "14:39",
        "maghrib": "17:00",
        "isha": "18:20",
    }
    for key, want in expected.items():
        got = times.get(key).strftime("%H:%M")
        check(f"{key} {want}", got == want, f"got {got}")

    check("times are ordered", all(
        times.get(a) < times.get(b)
        for a, b in zip(
            ["fajr", "sunrise", "dhuhr", "asr", "maghrib"],
            ["sunrise", "dhuhr", "asr", "maghrib", "isha"],
        )
    ))
    check(
        "all methods compute",
        all(
            calculate_times(
                latitude=cairo.latitude,
                longitude=cairo.longitude,
                timezone=cairo.timezone,
                day=date(2026, 6, 21),
                method=key,
            )["isha"]
            > calculate_times(
                latitude=cairo.latitude,
                longitude=cairo.longitude,
                timezone=cairo.timezone,
                day=date(2026, 6, 21),
                method=key,
            )["maghrib"]
            for key in METHODS
        ),
    )

    # next prayer / current window
    middle = times.fajr + (times.sunrise - times.fajr) / 2
    check("next prayer skips sunrise", times.next_prayer(middle)[0] == "dhuhr")
    check("current window is fajr", times.current_prayer(middle) == "fajr")
    midday = times.dhuhr + timedelta(minutes=30)
    check("midday window is dhuhr", times.current_prayer(midday) == "dhuhr")
    sunset = times.maghrib + timedelta(minutes=15)
    check("sunset window is maghrib", times.current_prayer(sunset) == "maghrib")
    late = times.isha + timedelta(hours=1)
    check("after isha -> no next prayer", times.next_prayer(late) is None)
    check("after isha -> current isha", times.current_prayer(late) == "isha")
    before_dawn = times.fajr - timedelta(minutes=30)
    check("pre-dawn current is isha", times.current_prayer(before_dawn) == "isha")

    # Other cities / DST sanity
    for key in ("alexandria", "aswan", "sharm", "luxor"):
        city = CITIES[key]
        t = prayer_times_for(
            city=city.name_ar,
            country="مصر",
            latitude=city.latitude,
            longitude=city.longitude,
            timezone=city.timezone,
            day=date(2026, 7, 1),
        )
        check(f"{key} computes", t.fajr.hour == 3 or t.fajr.hour == 4, str(t.fajr))

    # ------------------------------------------------------------------ #
    print("\n== embeds ==")
    embed = embeds.prayer_embed(times, hijri="٣ جمادى الأولى ١٤٤٨ هـ")
    check("prayer embed title", "مواقيت الصلاة" in (embed.title or ""))
    check("prayer embed fields", len(embed.fields) >= 2, str(len(embed.fields)))
    check("embed fits 6000 chars", len(embed) <= 6000, str(len(embed)))

    home = embeds.azkar_home_embed(data.ordered(), total=total)
    check("azkar home fields", len(home.fields) == 5, str(len(home.fields)))
    check("azkar home fits", len(home) <= 6000, str(len(home)))

    for category in data.ordered():
        for index in range(len(category.items)):
            item_embed = embeds.azkar_item_embed(category, index, 0)
            if len(item_embed) > 6000:
                check(f"azkar embed {category.key}#{index}", False, str(len(item_embed)))
    check("all azkar embeds fit 6000", not any(f.startswith("azkar embed") for f in FAILURES))

    # ------------------------------------------------------------------ #
    print("\n== arabic utils ==")
    check("arabic digits", ar.ar_number(123) == "١٢٣")
    check("arabic date", "نوفمبر" in ar.arabic_date(date(2026, 11, 14)))
    check("hijri format", "هـ" in ar.hijri_text(3, 5, 1448))
    check("progress bar full", ar.progress_bar(10, 10) == "▓" * 10)
    check("progress bar empty", ar.progress_bar(0, 10) == "░" * 10)
    check("hijri approx sane", 1440 < ar.hijri_approx(date(2026, 11, 14))[2] < 1460)

    # ------------------------------------------------------------------ #
    print("\n== discord objects ==")
    import discord

    bot = None
    try:
        from salahbot.bot import SalahBot
        from salahbot.config import Settings

        bot = SalahBot(Settings(token="dummy-token-for-offline-checks"))
        check("bot constructs", bot.user is None)
        check("azkar attached", len(bot.azkar.ordered()) == 5)
        launcher = AzkarLauncherView(bot)
        check("launcher has 5 buttons", len(launcher.children) == 5, str(len(launcher.children)))
        check("launcher is persistent", launcher.timeout is None)
        for child in launcher.children:
            check(
                f"custom_id {child.custom_id}",
                bool(getattr(child, "custom_id", None)),
            )

        view = PrayerView(
            bot,
            city_key="cairo",
            day=date.today(),
            method="egypt",
            author=discord.Object(id=1),
        )
        check("prayer view has 3 buttons", len(view.children) == 3)
    finally:
        if bot is not None:
            bot.store.save()

    # ------------------------------------------------------------------ #
    print("\n== CLI --check ==")
    import subprocess

    result = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(ROOT),
    )
    combined = (result.stdout or "") + (result.stderr or "")
    check("--check exits without a token", result.returncode == 1, f"rc={result.returncode}")
    check("--check reports missing token", "DISCORD_TOKEN is not set" in combined)
    check("--check prints banner", "Salah" in combined or "salah" in combined)

    # ------------------------------------------------------------------ #
    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} check(s) failed:")
        for name in FAILURES:
            print(f"   - {name}")
        return 1
    print("✅ all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
