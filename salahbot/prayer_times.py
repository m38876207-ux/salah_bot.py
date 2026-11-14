"""
Prayer time calculation engine (no external services required).

The maths follows the standard astronomical method used by PrayTimes.org
(Meeus solar coordinates + hour-angle computation), which is accurate to
about a minute for mid-latitude locations such as Egypt.

Only the Python standard library is used, so this module can be imported
and tested without installing anything.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# --------------------------------------------------------------------------- #
# Calculation methods
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Method:
    """A prayer-time calculation convention."""

    key: str
    name: str
    name_ar: str
    fajr_angle: float
    isha_angle: float | None = None  # None => isha_interval is used instead
    isha_interval: float | None = None  # minutes after maghrib
    asr_factor: float = 1.0  # 1.0 = Shafi'i / Maliki / Hanbali, 2.0 = Hanafi


METHODS: dict[str, Method] = {
    "egypt": Method(
        "egypt",
        "Egyptian General Authority of Survey",
        "الهيئة المصرية العامة للمساحة",
        fajr_angle=19.5,
        isha_angle=17.5,
    ),
    "mwl": Method(
        "mwl",
        "Muslim World League",
        "رابطة العالم الإسلامي",
        fajr_angle=18.0,
        isha_angle=17.0,
    ),
    "isna": Method(
        "isna",
        "Islamic Society of North America",
        "الجمعية الإسلامية لأمريكا الشمالية",
        fajr_angle=15.0,
        isha_angle=15.0,
    ),
    "umm_al_qura": Method(
        "umm_al_qura",
        "Umm al-Qura, Makkah",
        "أم القرى - مكة المكرمة",
        fajr_angle=18.5,
        isha_interval=90.0,
    ),
    "karachi": Method(
        "karachi",
        "University of Islamic Sciences, Karachi",
        "جامعة العلوم الإسلامية - كراتشي",
        fajr_angle=18.0,
        isha_angle=18.0,
    ),
    "dubai": Method(
        "dubai",
        "Dubai",
        "دبي",
        fajr_angle=18.2,
        isha_angle=18.2,
    ),
    "turkey": Method(
        "turkey",
        "Diyanet (Turkey)",
        "رئاسة الشؤون الدينية التركية",
        fajr_angle=18.0,
        isha_angle=17.0,
    ),
}

DEFAULT_METHOD = "egypt"

PRAYER_KEYS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")

PRAYER_NAMES_EN = {
    "fajr": "Fajr",
    "sunrise": "Sunrise",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "maghrib": "Maghrib",
    "isha": "Isha",
}

PRAYER_NAMES_AR = {
    "fajr": "الفجر",
    "sunrise": "الشروق",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}


# --------------------------------------------------------------------------- #
# Solar position
# --------------------------------------------------------------------------- #


def julian_day(year: int, month: int, day: int) -> float:
    """Julian Day at 00:00 UT for a Gregorian date."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def sun_position(jd: float) -> tuple[float, float]:
    """Return (declination in degrees, equation of time in minutes).

    ``jd`` is a Julian Day (UT).  Meeus, *Astronomical Algorithms*, eq. 25.2-25.4
    (low-precision solar coordinates, ~0.01° / ~4 s of time).
    """
    d = jd - 2451545.0

    # Mean anomaly (degrees).
    g = math.radians((357.529 + 0.98560028 * d) % 360.0)
    # Mean longitude (degrees, 0..360).
    q = (280.459 + 0.98564736 * d) % 360.0

    # Apparent (true) longitude of the sun, degrees.
    lam = (q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0
    lam_rad = math.radians(lam)

    # Obliquity of the ecliptic (degrees, with a slow linear drift).
    eps_rad = math.radians(23.439 - 0.00000036 * d)

    # Right ascension, in degrees (0..360).
    ra_deg = math.degrees(
        math.atan2(
            math.cos(eps_rad) * math.sin(lam_rad), math.cos(lam_rad)
        )
    ) % 360.0

    # Equation of time: (mean longitude - right ascension) expressed as an
    # angle, converted to minutes of time (1° = 4 min).  Both quantities are
    # kept in degrees here, which is the classic form of the formula.
    eqt = ((q - ra_deg + 180.0) % 360.0) - 180.0
    eqt_minutes = eqt * 4.0

    decl = math.degrees(math.asin(math.sin(eps_rad) * math.sin(lam_rad)))
    return decl, eqt_minutes


def _hour_angle(angle: float, lat: float, decl: float) -> float | None:
    """Hour angle (hours) between solar noon and the given solar altitude.

    ``angle`` is the (signed) solar altitude in degrees: sunrise/sunset use
    -0.833° (refraction + solar disc), Fajr/Isha their twilight angles, and
    Asr its shadow-derived altitude.

    Returns ``None`` when the sun never reaches that altitude on that day
    (polar day/night) — the caller then applies a fallback.
    """
    # sin(alt) = sin(lat)sin(dec) + cos(lat)cos(dec)cos(H), solved for cos(H).
    cos_h = (
        math.sin(math.radians(angle))
        - math.sin(math.radians(lat)) * math.sin(math.radians(decl))
    ) / (math.cos(math.radians(lat)) * math.cos(math.radians(decl)))
    if cos_h > 1.0 or cos_h < -1.0:
        return None
    return math.degrees(math.acos(cos_h)) / 15.0


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PrayerTimes:
    """All prayer times for one day at one location (timezone-aware)."""

    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    method: str
    date: date
    times: dict[str, datetime] = field(default_factory=dict)
    source: str = "calculated"

    # -- convenience accessors ------------------------------------------- #
    def get(self, key: str) -> datetime | None:
        return self.times.get(key)

    @property
    def fajr(self) -> datetime:
        return self.times["fajr"]

    @property
    def sunrise(self) -> datetime:
        return self.times["sunrise"]

    @property
    def dhuhr(self) -> datetime:
        return self.times["dhuhr"]

    @property
    def asr(self) -> datetime:
        return self.times["asr"]

    @property
    def maghrib(self) -> datetime:
        return self.times["maghrib"]

    @property
    def isha(self) -> datetime:
        return self.times["isha"]

    # -- helpers --------------------------------------------------------- #
    def next_prayer(
        self, now: datetime | None = None
    ) -> tuple[str, datetime] | None:
        """The next prayer (fajr..isha) after ``now``.

        Returns ``None`` if every prayer of the day has passed — the caller
        should then look at tomorrow's Fajr.
        """
        now = now or datetime.now(ZoneInfo(self.timezone))
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(self.timezone))
        for key in PRAYER_KEYS:
            if key == "sunrise":
                continue
            if self.times[key] > now:
                return key, self.times[key]
        return None

    def current_prayer(self, now: datetime | None = None) -> str:
        """Which prayer window we are inside right now."""
        now = now or datetime.now(ZoneInfo(self.timezone))
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(self.timezone))
        order = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
        current = "isha"
        for key in order:
            if now >= self.times[key]:
                current = key
        # Between midnight and Fajr we are still in the Isha window.
        return current


# --------------------------------------------------------------------------- #
# The calculator
# --------------------------------------------------------------------------- #


def calculate_times(
    *,
    latitude: float,
    longitude: float,
    timezone: str,
    day: date,
    method: str = DEFAULT_METHOD,
    asr_factor: float | None = None,
    offsets: dict[str, int] | None = None,
) -> dict[str, datetime]:
    """Compute the six daily times as timezone-aware datetimes.

    ``offsets`` lets a caller nudge individual prayers by minutes, e.g.
    ``{"dhuhr": 2}`` to add two minutes to Dhuhr.
    """
    method_def = METHODS.get(method, METHODS[DEFAULT_METHOD])
    factor = method_def.asr_factor if asr_factor is None else asr_factor
    tz = ZoneInfo(timezone)

    jd = julian_day(day.year, day.month, day.day)
    decl, eqt = sun_position(jd)

    # Solar noon as local clock time: 12:00 at the reference meridian, shifted
    # for the longitude difference (4 min per degree, east is earlier), the
    # equation of time, and the zone offset (local = UTC + offset).
    noon_minutes = (
        12.0 * 60.0 - 4.0 * longitude - eqt + _tz_offset_hours(day, tz) * 60.0
    )

    def at(minutes_from_midnight: float) -> datetime:
        total = int(round(minutes_from_midnight))
        day_offset, remainder = divmod(total, 24 * 60)
        base = datetime.combine(day, time(0, 0), tzinfo=tz)
        return base + timedelta(days=day_offset, minutes=remainder)

    # Negative altitudes: sunrise/sunset account for refraction + solar radius.
    sunrise_ha = _hour_angle(-0.833, latitude, decl)
    fajr_ha = _hour_angle(-method_def.fajr_angle, latitude, decl)
    isha_ha = (
        _hour_angle(-method_def.isha_angle, latitude, decl)
        if method_def.isha_angle is not None
        else None
    )

    # Asr: the shadow of a vertical object is `factor` times its height.
    #   cot(alt) = factor + tan(|lat - dec|)
    # where |lat - dec| is the solar zenith distance at local noon.
    noon_zenith = abs(latitude - decl)
    asr_angle = math.degrees(
        math.atan(
            1.0 / (factor + math.tan(math.radians(noon_zenith)))
        )
    )
    # Asr falls in the afternoon, so the altitude is *above* the horizon and
    # the hour angle is already measured on the afternoon branch.
    asr_ha = _hour_angle(asr_angle, latitude, decl)

    # Fallbacks for high latitudes where a twilight angle is never reached.
    if fajr_ha is None:
        fajr_ha = sunrise_ha if sunrise_ha is not None else 1.5
    if isha_ha is None:
        isha_ha = sunrise_ha if sunrise_ha is not None else 1.5
    if sunrise_ha is None:
        sunrise_ha = 6.0
    if asr_ha is None:
        asr_ha = 3.5

    raw = {
        "fajr": noon_minutes - fajr_ha * 60.0,
        "sunrise": noon_minutes - sunrise_ha * 60.0,
        "dhuhr": noon_minutes,
        "asr": noon_minutes + asr_ha * 60.0,
        "maghrib": noon_minutes + sunrise_ha * 60.0,
        "isha": (
            noon_minutes + isha_ha * 60.0
            if method_def.isha_angle is not None
            else noon_minutes + sunrise_ha * 60.0 + (method_def.isha_interval or 90.0)
        ),
    }

    result: dict[str, datetime] = {}
    for key, minutes in raw.items():
        extra = (offsets or {}).get(key, 0)
        result[key] = at(minutes + extra)
    return result


def _tz_offset_hours(day: date, tz: ZoneInfo) -> float:
    """UTC offset of ``tz`` at noon on ``day`` (handles DST correctly)."""
    noon = datetime.combine(day, time(12, 0), tzinfo=tz)
    return noon.utcoffset().total_seconds() / 3600.0


def prayer_times_for(
    *,
    city: str,
    country: str,
    latitude: float,
    longitude: float,
    timezone: str,
    day: date,
    method: str = DEFAULT_METHOD,
    asr_factor: float | None = None,
    offsets: dict[str, int] | None = None,
) -> PrayerTimes:
    """Calculate the full :class:`PrayerTimes` record for a location."""
    return PrayerTimes(
        city=city,
        country=country,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        method=method,
        date=day,
        times=calculate_times(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            day=day,
            method=method,
            asr_factor=asr_factor,
            offsets=offsets,
        ),
        source="calculated",
    )


# --------------------------------------------------------------------------- #
# Small utilities used by the bot
# --------------------------------------------------------------------------- #


def format_time_24(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def format_time_12(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def human_delta(target: datetime, now: datetime | None = None) -> str:
    """'in 1h 24m' / '12m ago' style string."""
    if now is None:
        now = datetime.now(target.tzinfo)
    delta = target - now
    seconds = int(delta.total_seconds())
    future = seconds >= 0
    seconds = abs(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours and minutes:
        text = f"{hours}h {minutes}m"
    elif hours:
        text = f"{hours}h"
    elif minutes:
        text = f"{minutes}m"
    else:
        text = "less than a minute"
    return f"in {text}" if future else f"{text} ago"
