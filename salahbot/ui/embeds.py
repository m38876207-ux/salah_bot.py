"""Embed builders.  Pure functions — easy to unit-test without Discord."""

from __future__ import annotations

from datetime import datetime

import discord

from ..azkar import Category, Zikr
from ..config import ACCENT, ARABIC_LABELS, COLOR_BLUE, COLOR_GOLD, EMOJI, TAGLINE
from ..prayer_times import PRAYER_KEYS, PrayerTimes
from ..utils.ar import (
    ar_number,
    arabic_date,
    human_seconds,
    progress_bar,
)

PRAYER_BUTTON_TIMEOUT = 300


def _discord_ts(dt: datetime, style: str = "t") -> str:
    return f"<t:{int(dt.timestamp())}:{style}>"


def _footer(extra: str) -> str:
    return f"{extra}\n{TAGLINE}"


# --------------------------------------------------------------------------- #
# Prayer times
# --------------------------------------------------------------------------- #


def prayer_embed(
    times: PrayerTimes,
    *,
    hijri: str | None = None,
    next_prayer: tuple[str, datetime] | None = None,
    now: datetime | None = None,
    title_suffix: str = "",
) -> discord.Embed:
    """The main /prayer embed: a six-row table plus live countdown."""
    now = now or datetime.now(times.fajr.tzinfo)
    city_label = f"{times.city} • {times.country}"
    embed = discord.Embed(
        title=f"🕌 مواقيت الصلاة — {times.city}{title_suffix}",
        description=(
            f"**{arabic_date(times.date)}**\n"
            f"{hijri or ''}\n"
            f"📍 {city_label}  ·  `{times.latitude:.4f}, {times.longitude:.4f}`"
        ),
        color=ACCENT,
    )

    current = times.current_prayer(now)

    lines: list[str] = []
    for key in PRAYER_KEYS:
        when = times.get(key)
        if when is None:
            continue
        name_ar, name_en = ARABIC_LABELS[key]
        marker = " **← الآن**" if key == current and key != "sunrise" else ""
        lines.append(
            f"{EMOJI[key]} **{name_ar}** · {name_en}\n"
            f"`{when.strftime('%H:%M')}` · {_discord_ts(when, 'R')}{marker}"
        )
    embed.add_field(name="جدول المواقيت", value="\n".join(lines), inline=False)

    if next_prayer is None:
        next_prayer = times.next_prayer(now)
    if next_prayer is not None:
        key, when = next_prayer
        name_ar, name_en = ARABIC_LABELS[key]
        delta = int((when - now).total_seconds())
        embed.add_field(
            name=f"⏳ الصلاة القادمة: {name_ar}",
            value=(
                f"{EMOJI[key]} **{name_en}** — في **{human_seconds(delta)}**\n"
                f"🕒 {_discord_ts(when, 't')} بتوقيتك  ({_discord_ts(when, 'R')})"
            ),
            inline=False,
        )

    embed.set_footer(text=_footer("المواقيت محسوبة فلكيًا — اضغط 🔄 للتحديث"))
    return embed


def compact_prayer_embed(
    times: PrayerTimes, *, hijri: str | None = None, label: str = "مواقيت اليوم"
) -> discord.Embed:
    """Small table used for reminders and previews."""
    embed = discord.Embed(
        title=f"🕌 {label} — {times.city}",
        description=f"**{arabic_date(times.date)}**\n{hijri or ''}",
        color=ACCENT,
    )
    body = []
    for key in PRAYER_KEYS:
        when = times.get(key)
        if when is None:
            continue
        name_ar, _ = ARABIC_LABELS[key]
        body.append(f"{EMOJI[key]} {name_ar}: `{when.strftime('%H:%M')}` {_discord_ts(when, 'R')}")
    embed.add_field(name="المواقيت", value="\n".join(body), inline=False)
    embed.set_footer(text=TAGLINE)
    return embed


def error_embed(message: str, *, title: str = "حدث خطأ") -> discord.Embed:
    return discord.Embed(title=f"⚠️ {title}", description=message, color=0xB3261E)


def info_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_BLUE)


# --------------------------------------------------------------------------- #
# Azkar
# --------------------------------------------------------------------------- #


def azkar_home_embed(
    categories: list[Category], *, total: int | None = None
) -> discord.Embed:
    """Overview of every category, used by /azkar without a category."""
    embed = discord.Embed(
        title="📿 الأذكار",
        description=(
            "اختر القسم من القائمة بالأسفل، أو استخدم الأمر مباشرة:\n"
            "`/azkar category:أذكار الصباح`\n\n"
            f"إجمالي الأذكار المحفوظة: **{ar_number(total or len(categories))}**"
        ),
        color=COLOR_GOLD,
    )
    for category in categories:
        embed.add_field(
            name=category.label,
            value=(
                f"{category.description_ar}\n"
                f"`{ar_number(len(category.items))}` ذكرًا · "
                f"`{ar_number(category.total_repetitions)}` تكرارًا"
            ),
            inline=True,
        )
    embed.set_footer(text=_footer("استخدم القائمة لاختيار القسم"))
    return embed


def azkar_item_embed(
    category: Category,
    index: int,
    count: int,
    *,
    viewer: str | None = None,
) -> discord.Embed:
    """One zikr, with a repetition counter."""
    item: Zikr = category.items[index]
    total = len(category.items)
    done = count >= item.count

    embed = discord.Embed(
        title=f"{category.emoji} {category.name_ar}  ·  {index + 1}/{total}",
        description=item.text,
        color=0x2E7D32 if done else COLOR_GOLD,
    )
    embed.add_field(
        name="🔁 التكرار",
        value=(
            f"**{ar_number(count)} / {ar_number(item.count)}**\n"
            f"{progress_bar(count, item.count)}\n"
            f"{'✅ تم بحمد الله — اضغط «التالي»' if done else 'اضغط «سُبْحَانَ اللَّهِ» لتسجيل تكرار'}"
        ),
        inline=True,
    )
    if item.source:
        embed.add_field(name="📖 المصدر", value=item.source, inline=True)
    else:
        embed.add_field(name="📖 المصدر", value="—", inline=True)
    if item.note:
        embed.add_field(name="📝 ملاحظة", value=item.note, inline=False)

    footer = f"{category.name_ar} · {index + 1}/{total}"
    if viewer:
        footer = f"{viewer} · {footer}"
    embed.set_footer(text=_footer(footer))
    return embed


def azkar_finished_embed(category: Category) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ أنهيت {category.name_ar}",
        description=(
            "جعل الله لك منها أجرًا عظيمًا، وتقبل منك صالح الأعمال 🤲\n\n"
            f"إجمالي التكرارات في هذا القسم: **{ar_number(category.total_repetitions)}**"
        ),
        color=0x2E7D32,
    )
    embed.set_footer(text=TAGLINE)
    return embed


def azkar_reminder_embed(category: Category, *, label: str) -> discord.Embed:
    items = "\n".join(
        f"• {item.text.splitlines()[0][:120]}" for item in category.items[:4]
    )
    embed = discord.Embed(
        title=f"{category.emoji} {label}: {category.name_ar}",
        description=f"{items}\n\n*…وغيرها* — استخدم `/azkar` لقراءتها كاملة.",
        color=COLOR_GOLD,
    )
    embed.set_footer(text=TAGLINE)
    return embed


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #


def help_embed(prefix_ok: bool = True) -> discord.Embed:
    embed = discord.Embed(
        title="🕌 بوت مواقيت الصلاة والأذكار",
        description=(
            "بوت لتوقيت الصلاة في **مصر** وجميع المدن المصرية، مع أذكار الصباح "
            "والمساء وأذكار بعد الصلاة والنوم والاستيقاظ.\n\n"
            "**المواقيت محسوبة فلكيًا** (طريقة الهيئة المصرية العامة للمساحة) "
            "دون الحاجة لأي خدمة خارجية."
        ),
        color=ACCENT,
    )
    embed.add_field(
        name="🕌 مواقيت الصلاة",
        value=(
            "`/prayer` — مواقيت اليوم لأي مدينة مصرية\n"
            "`/next` — الصلاة القادمة والعد التنازلي\n"
            "`/week` — جدول الأسبوع كاملًا\n"
            "`/methods` — طرق الحساب المتاحة"
        ),
        inline=False,
    )
    embed.add_field(
        name="📿 الأذكار",
        value=(
            "`/azkar` — قائمة الأذكار والأقسام\n"
            "`/azkar category:...` — قراءة قسم مع عدّاد التكرار\n"
            "`/zikr` — ذكر عشوائي\n"
            "`/reminders` — تفعيل تذكير أذكار الصباح والمساء"
        ),
        inline=False,
    )
    return embed


def next_prayer_embed(
    times: PrayerTimes,
    next_prayer: tuple[str, datetime],
    *,
    now: datetime,
) -> discord.Embed:
    key, when = next_prayer
    name_ar, name_en = ARABIC_LABELS[key]
    delta = int((when - now).total_seconds())
    embed = discord.Embed(
        title=f"{EMOJI[key]} الصلاة القادمة — {name_ar}",
        description=(
            f"**{name_en}** بعد **{human_seconds(delta)}**\n"
            f"🕒 {_discord_ts(when, 't')} بتوقيتك ({_discord_ts(when, 'R')})\n"
            f"📍 {times.city} · {arabic_date(times.date)}"
        ),
        color=COLOR_GOLD,
    )
    embed.set_footer(text=TAGLINE)
    return embed


def week_embed(rows: list[tuple[datetime, PrayerTimes]]) -> discord.Embed:
    lines = ["`اليوم   فجر  شروق  ظهر  عصر  مغرب  عشاء`"]
    for day, times in rows:
        cells = [
            times.get(key).strftime("%H:%M") if times.get(key) else "--:--"
            for key in PRAYER_KEYS
        ]
        label = f"{day.day:>2}/{day.month:02d}"
        lines.append(f"`{label}` " + " ".join(f"`{c}`" for c in cells))
    embed = discord.Embed(
        title="📅 مواقيت الأسبوع",
        description="\n".join(lines),
        color=COLOR_BLUE,
    )
    embed.set_footer(text=TAGLINE)
    return embed
