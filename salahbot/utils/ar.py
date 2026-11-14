"""Arabic numeral / text helpers used across embeds."""

from __future__ import annotations

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

_DAYS_AR = [
    "الاثنين",
    "الثلاثاء",
    "الأربعاء",
    "الخميس",
    "الجمعة",
    "السبت",
    "الأحد",
]

_MONTHS_AR = [
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
]

HIJRI_MONTHS = [
    "محرم",
    "صفر",
    "ربيع الأول",
    "ربيع الآخر",
    "جمادى الأولى",
    "جمادى الآخرة",
    "رجب",
    "شعبان",
    "رمضان",
    "شوال",
    "ذو القعدة",
    "ذو الحجة",
]


def ar_number(value: int | str) -> str:
    """Convert western digits to Arabic-Indic digits."""
    return str(value).translate(AR_DIGITS)


def arabic_date(dt) -> str:
    """e.g. 'السبت ١٤ نوفمبر ٢٠٢٦'."""
    return (
        f"{_DAYS_AR[dt.weekday()]} {ar_number(dt.day)} "
        f"{_MONTHS_AR[dt.month - 1]} {ar_number(dt.year)}"
    )


def gregorian_short(dt) -> str:
    """e.g. '14 Nov 2026' (English, for mixed audiences)."""
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    return f"{dt.day} {months[dt.month - 1]} {dt.year}"


def gregorian_full(dt) -> str:
    """e.g. 'Saturday, 14 November 2026'."""
    days = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    months = [
        "January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December",
    ]
    return f"{days[dt.weekday()]}, {dt.day} {months[dt.month - 1]} {dt.year}"


def hijri_text(day: int, month: int, year: int) -> str:
    """Format a Hijri date, e.g. '٣ جمادى الأولى ١٤٤٨ هـ'."""
    month_name = HIJRI_MONTHS[(month - 1) % 12]
    return f"{ar_number(day)} {month_name} {ar_number(year)} هـ"


def progress_bar(current: int, total: int, width: int = 10) -> str:
    """A simple text progress bar, e.g. '▓▓▓▓▓▓░░░░'."""
    if total <= 0:
        return "░" * width
    filled = min(width, max(0, round(width * current / total)))
    return "▓" * filled + "░" * (width - filled)


def human_seconds(total_seconds: int) -> str:
    """99 -> 'دقيقة و٣٩ ثانية' style short form."""
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{ar_number(hours)} س {ar_number(minutes)} د"
    if minutes:
        return f"{ar_number(minutes)} د {ar_number(secs)} ث"
    return f"{ar_number(secs)} ث"


def hijri_approx(gregorian_date) -> tuple[int, int, int]:
    """Approximate Hijri conversion (Kuwaiti algorithm), used when offline.

    Accurate to a day or two; the AlAdhan API value is preferred when
    available.
    """
    year, month, day = (
        gregorian_date.year,
        gregorian_date.month,
        gregorian_date.day,
    )
    if month < 3:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd = (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day
        + b
        - 1524
    )
    # Julian day -> Islamic calendar (integer arithmetic, civil epoch).
    days = jd - 1948440 + 10632
    n = (days - 1) // 10631
    days = days - 10631 * n + 354
    j = (10985 - days) // 5316 * ((50 * days) // 17719) + (
        days // 5670
    ) * ((43 * days) // 15238)
    days = (
        days
        - (30 - j) // 15 * ((17719 * j) // 50)
        - (j // 16) * ((15238 * j) // 43)
        + 29
    )
    h_month = (24 * days) // 709
    h_day = days - (709 * h_month) // 24
    h_year = 30 * n + j - 30
    return h_day, h_month, h_year
