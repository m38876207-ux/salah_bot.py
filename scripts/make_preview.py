"""
Generate Discord-style preview images for the README.

    pip install pillow arabic-reshaper python-bidi
    python scripts/make_preview.py

Output: docs/preview-prayer.png, docs/preview-azkar.png
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = ROOT / "docs"
OUT_DIR.mkdir(exist_ok=True)

# -- palette (Discord dark theme) ------------------------------------------- #
BG = (49, 51, 56)
EMBED_BG = (43, 45, 49)
GREEN = (31, 139, 76)
GOLD = (201, 162, 39)
BLURPLE = (88, 101, 242)
TEXT = (219, 222, 225)
MUTED = (148, 155, 164)
WHITE = (255, 255, 255)
DIVIDER = (63, 65, 70)
SELECT_BG = (54, 56, 62)
BTN_GREY = (78, 80, 88)
BTN_RED = (139, 47, 47)
BTN_GREEN = (36, 128, 72)
HILITE = (47, 60, 51)
GREEN_TEXT = (88, 220, 140)

FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {
    "latin": FONT_DIR / "segoeui.ttf",
    "latin_bold": FONT_DIR / "segoeuib.ttf",
    "arabic": FONT_DIR / "tahoma.ttf",
    "arabic_bold": FONT_DIR / "tahomabd.ttf",
    "emoji": FONT_DIR / "seguiemj.ttf",
}

S = 2  # supersampling factor

EMOJI = re.compile(
    "([\U0001F300-\U0001FAFF\U00002600-\U000027BF\u23E9-\u23FA\u2B00-\u2BFF\ufe0f]+)"
)
ARABIC = re.compile(r"[\u0600-\u06FF]")


# --------------------------------------------------------------------------- #
# low-level helpers
# --------------------------------------------------------------------------- #


def _font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS[key]), size * S)


def _probe() -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(Image.new("RGB", (1, 1)))


def shaped(text: str, *, rtl: bool = True) -> str:
    if not text or not ARABIC.search(text):
        return text
    return get_display(arabic_reshaper.reshape(("\u200f" if rtl else "") + text))


def _plain_width(text: str, key: str, size: int) -> int:
    if not text:
        return 0
    draw = _probe()
    return (draw.textbbox((0, 0), shaped(text), font=_font(key, size))[2]) // S


def width(text: str, key: str, size: int) -> int:
    """Pixel width of a line: emoji prefix (if any) + shaped text."""
    emojis = "".join(EMOJI.findall(text))
    body = EMOJI.sub("", text).strip()
    total = 0
    if emojis:
        total += _font("emoji", size).getbbox(emojis)[2] + 4 * S
    total += _plain_width(body, key, size) * S
    return total // S


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    content: str,
    *,
    key: str = "arabic",
    size: int = 13,
    color=TEXT,
    right_edge: float | None = None,
) -> None:
    """Draw one line: emoji rendered with the colour font, then shaped text."""
    x = xy[0]
    if right_edge is not None:
        x = right_edge - width(content, key, size)

    emojis = "".join(EMOJI.findall(content))
    body = EMOJI.sub("", content).strip()

    cx = x * S
    if emojis:
        ef = _font("emoji", size)
        draw.text((cx, xy[1] * S), emojis, font=ef, fill=color, embedded_color=True)
        cx += ef.getbbox(emojis)[2] + 4 * S

    if not body:
        return
    f = _font(key, size)
    draw.text((cx, xy[1] * S), shaped("\u200f" + body, rtl=True), font=f, fill=color)


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, w=1):
    x0, y0, x1, y1 = [v * S for v in box]
    draw.rounded_rectangle(
        (x0, y0, x1, y1), radius=radius * S, fill=fill, outline=outline, width=w * S
    )


def header(canvas: Image.Image, w: int, stamp: str) -> None:
    draw = ImageDraw.Draw(canvas)
    ax, ay, r = 16, 12, 18
    draw.ellipse((ax * S, ay * S, (ax + 2 * r) * S, (ay + 2 * r) * S), fill=BLURPLE)
    draw.text(
        (ax * S + 12, ay * S + 6),
        "🕌",
        font=_font("emoji", 18),
        embedded_color=True,
    )
    text(draw, (ax + 2 * r + 10, ay + 1), "salah-bot", key="latin_bold", size=15, color=WHITE)
    text(
        draw,
        (ax + 2 * r + 10, ay + 20),
        "APP · بوت",
        key="latin",
        size=9,
        color=MUTED,
    )
    for i in range(3):
        cx = w - 46 + i * 9
        draw.ellipse(((cx - 1.5) * S, 21 * S, (cx + 1.5) * S, 24 * S), fill=MUTED)


def buttons(
    draw: ImageDraw.ImageDraw,
    y: float,
    x_start: float,
    items: list[tuple[str, tuple[int, int, int]]],
    *,
    height: int = 30,
) -> None:
    x = x_start
    for label, color in items:
        w = width(label, "arabic", 11) + 28
        rounded(draw, (x, y, x + w, y + height), 4, color)
        text(draw, (x + 14, y + 7), label, size=11, color=WHITE)
        x += w + 8


# --------------------------------------------------------------------------- #
# Card 1: /prayer
# --------------------------------------------------------------------------- #


def prayer_card() -> Path:
    W, H = 640, 640
    canvas = Image.new("RGB", (W * S, H * S), BG)
    draw = ImageDraw.Draw(canvas)
    header(canvas, W, "اليوم ١١:١٢ ص")

    top, bottom = 56, H - 12
    rounded(draw, (14, top, W - 16, bottom), 6, EMBED_BG)
    rounded(draw, (14, top, 19, bottom), 2, GREEN)

    L, R = 34, W - 30
    y = 72.0

    text(draw, (L, y), "مواقيت الصلاة — القاهرة", size=18, color=WHITE)
    y += 32
    text(draw, (L, y), "السبت ١٤ نوفمبر ٢٠٢٦", size=12, color=TEXT)
    y += 20
    text(draw, (L, y), "٣ جمادى الأولى ١٤٤٨ هـ", size=12, color=GOLD)
    y += 20
    text(draw, (L, y), "30.0444, 31.2357", key="latin", size=9, color=MUTED)
    text(
        draw,
        (0, y),
        "مصر • القاهرة",
        size=10,
        color=MUTED,
        right_edge=R,
    )
    y += 22
    draw.line((L * S, y * S, R * S, y * S), fill=DIVIDER, width=S)
    y += 14

    text(draw, (L, y), "جدول المواقيت", size=12, color=TEXT)
    y += 26

    rows = [
        ("🌌", "الفجر", "Fajr", "04:49", "مرت ٦ س ٢٣ د", False),
        ("🌅", "الشروق", "Sunrise", "06:19", "مرت ٥ س ٠٠ د", False),
        ("☀️", "الظهر", "Dhuhr", "11:39", "بعد ١ س ٢٧ د", True),
        ("🌤️", "العصر", "Asr", "14:39", "", False),
        ("🌇", "المغرب", "Maghrib", "17:00", "", False),
        ("🌙", "العشاء", "Isha", "18:20", "", False),
    ]
    row_h = 50
    for glyph, name_ar, name_en, clock, rel, highlight in rows:
        if highlight:
            rounded(draw, (L - 8, y - 4, R, y + row_h - 8), 5, HILITE)
        text(draw, (L, y + 4), glyph, size=15, color=TEXT)
        text(draw, (L + 30, y - 2), name_ar, size=13, color=WHITE if highlight else TEXT)
        text(draw, (L + 30, y + 17), name_en, key="latin", size=9, color=MUTED)
        text(draw, (L + 118, y), clock, key="latin_bold", size=15, color=WHITE)
        if rel:
            text(draw, (L + 182, y + 5), rel, size=10, color=MUTED)
        if highlight:
            text(
                draw,
                (0, y + 7),
                "الآن",
                size=11,
                color=GREEN_TEXT,
                right_edge=R,
            )
        y += row_h

    draw.line((L * S, y * S, R * S, y * S), fill=DIVIDER, width=S)
    y += 14
    text(draw, (L, y), "الصلاة القادمة: الظهر", size=12, color=GOLD)
    y += 24
    text(draw, (L, y), "تبقى ١ س ٢٧ د", size=11, color=TEXT)
    text(draw, (0, y + 2), "Dhuhr", key="latin", size=8, color=MUTED, right_edge=R)
    y += 20
    text(draw, (L, y), "11:39 بتوقيتك", size=10, color=MUTED)

    y = bottom - 26
    draw.line((L * S, y * S, R * S, y * S), fill=DIVIDER, width=S)
    text(draw, (L, y + 8), "المواقيت محسوبة فلكيًا", size=9, color=MUTED)

    buttons(
        draw,
        bottom + 14,
        L,
        [
            ("◀ اليوم السابق", BTN_GREY),
            ("تحديث 🔄", BLURPLE),
            ("اليوم التالي ▶", BTN_GREY),
        ],
    )

    out = OUT_DIR / "preview-prayer.png"
    canvas.resize((W, H), Image.LANCZOS).save(out)
    return out


# --------------------------------------------------------------------------- #
# Card 2: /azkar
# --------------------------------------------------------------------------- #


def azkar_card() -> Path:
    W, H = 640, 690
    canvas = Image.new("RGB", (W * S, H * S), BG)
    draw = ImageDraw.Draw(canvas)
    header(canvas, W, "اليوم ١١:١٢ ص")

    top, bottom = 56, H - 12
    rounded(draw, (14, top, W - 16, bottom), 6, EMBED_BG)
    rounded(draw, (14, top, 19, bottom), 2, GOLD)

    L, R = 34, W - 30
    y = 72.0

    text(draw, (L, y), "أذكار الصباح · ٣/١٤", size=16, color=WHITE)
    y += 34

    body = [
        "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ،",
        "لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ،",
        "لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ.",
        "رَبِّ أَسْأَلُكَ خَيْرَ مَا فِي هَذَا الْيَوْمِ وَخَيْرَ مَا بَعْدَهُ،",
        "وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِي هَذَا الْيَوْمِ وَشَرِّ مَا بَعْدَهُ.",
    ]
    for paragraph in body:
        text(draw, (L, y), paragraph, size=13, color=TEXT)
        y += 25

    y += 12
    draw.line((L * S, y * S, R * S, y * S), fill=DIVIDER, width=S)
    y += 14

    text(draw, (L, y), "التكرار 🔁\ufe0f", size=12, color=TEXT)
    text(draw, (0, y), "٣ / ١٠", size=15, color=GOLD, right_edge=R)
    y += 28

    bar_h = 12
    rounded(draw, (L, y, R, y + bar_h), 6, (60, 62, 68))
    span = (R - L) * 0.3
    if span > 6:
        rounded(draw, (L, y, L + span, y + bar_h), 6, GOLD)
    y += bar_h + 10
    text(draw, (L, y), "اضغط «سُبْحَانَ اللَّهِ» لتسجيل تكرار", size=10, color=MUTED)

    y += 30
    text(draw, (L, y), "📖 رواه مسلم", size=11, color=GOLD)
    y += 24
    text(draw, (L, y), "📝 تُقال بعد صلاة الفجر إلى شروق الشمس", size=11, color=MUTED)

    y = bottom - 196
    rounded(draw, (L, y, L + 280, y + 40), 4, BLURPLE)
    text(draw, (L + 80, y + 11), "سُبْحَانَ اللَّهِ (١٠)", size=13, color=WHITE)

    y += 50
    buttons(draw, y, L, [("◀ السابق", BTN_GREY), ("التالي ▶", BTN_GREEN)])
    y += 40
    buttons(draw, y, L, [("من الأول 🔄", BTN_GREY), ("إغلاق ✖", BTN_RED)])
    y += 40

    rounded(draw, (L, y, R, y + 34), 4, SELECT_BG)
    text(draw, (L + 14, y + 8), "القسم الحالي: أذكار الصباح 📿", size=11, color=TEXT)

    fy = bottom - 24
    draw.line((L * S, fy * S, R * S, fy * S), fill=DIVIDER, width=S)
    text(
        draw,
        (L, fy + 7),
        "Tester · أذكار الصباح · 3/14",
        size=9,
        color=MUTED,
    )

    out = OUT_DIR / "preview-azkar.png"
    canvas.resize((W, H), Image.LANCZOS).save(out)
    return out


def main() -> int:
    for path in (prayer_card(), azkar_card()):
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
