"""
City database for the Egyptian prayer times bot.

`method`        : calculation method key (see salahbot.prayer_times.METHODS)
`asr`           : 1.0 = Shafi'i (Egypt default), 2.0 = Hanafi
`offsets`       : per-prayer minute tweaks, used to match local mosque timings
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, eq=False)
class City:
    """A location with its calculation preferences.

    ``eq=False`` keeps identity-based hashing so cities can be put in sets or
    used as dict keys even though they hold a mutable dict.
    """

    key: str
    name_ar: str
    name_en: str
    latitude: float
    longitude: float
    timezone: str = "Africa/Cairo"
    method: str = "egypt"
    asr: float = 1.0
    offsets: dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name_ar} ({self.name_en})"


# Coordinates are city-centre points. Timezone is Africa/Cairo for all of
# Egypt — the bot converts to Discord timestamps, so each viewer sees their
# own local time.
CITIES: dict[str, City] = {}


def _add(key: str, name_ar: str, name_en: str, lat: float, lon: float) -> None:
    CITIES[key] = City(key, name_ar, name_en, lat, lon)


_add("cairo", "القاهرة", "Cairo", 30.0444196, 31.2357116)
_add("giza", "الجيزة", "Giza", 30.0131, 31.2089)
_add("alexandria", "الإسكندرية", "Alexandria", 31.2001, 29.9187)
_add("shubra", "شبرا الخيمة", "Shubra El-Kheima", 30.1286, 31.2422)
_add("port-said", "بورسعيد", "Port Said", 31.2653, 32.3019)
_add("suez", "السويس", "Suez", 29.9668, 32.5498)
_add("ismailia", "الإسماعيلية", "Ismailia", 30.5965, 32.2715)
_add("mansoura", "المنصورة", "Mansoura", 31.0409, 31.3785)
_add("tanta", "طنطا", "Tanta", 30.7865, 31.0004)
_add("zagazig", "الزقازيق", "Zagazig", 30.5877, 31.5020)
_add("damanhour", "دمنهور", "Damanhour", 31.0341, 30.4682)
_add("kafr-elsheikh", "كفر الشيخ", "Kafr El-Sheikh", 31.1117, 30.9398)
_add("damietta", "دمياط", "Damietta", 31.4165, 31.8133)
_add("banha", "بنها", "Banha", 30.4598, 31.1848)
_add("shibin", "شبين الكوم", "Shibin El-Kom", 30.5540, 31.0090)
_add("fayoum", "الفيوم", "Fayoum", 29.3084, 30.8428)
_add("beni-suef", "بني سويف", "Beni Suef", 29.0661, 31.0994)
_add("minya", "المنيا", "Minya", 28.1099, 30.7503)
_add("asyut", "أسيوط", "Asyut", 27.1783, 31.1859)
_add("sohag", "سوهاج", "Sohag", 26.5591, 31.6957)
_add("qena", "قنا", "Qena", 26.1551, 32.7160)
_add("luxor", "الأقصر", "Luxor", 25.6872, 32.6396)
_add("aswan", "أسوان", "Aswan", 24.0889, 32.8998)
_add("hurghada", "الغردقة", "Hurghada", 27.2579, 33.8116)
_add("sharm", "شرم الشيخ", "Sharm El-Sheikh", 27.9158, 34.3300)
_add("dahab", "دهب", "Dahab", 28.5091, 34.5136)
_add("marsa-alam", "مرسى علم", "Marsa Alam", 25.0670, 34.8930)
_add("el-arish", "العريش", "El-Arish", 31.1316, 33.7984)
_add("matrouh", "مرسى مطروح", "Marsa Matrouh", 31.3543, 27.2373)
_add("siwa", "سيوة", "Siwa", 29.2032, 25.5195)
_add("new-valley", "الخارجة", "El-Kharga (New Valley)", 25.4514, 30.5464)
_add("new-cairo", "القاهرة الجديدة", "New Cairo", 30.0300, 31.4700)
_add("6-october", "6 أكتوبر", "6th of October", 29.9275, 30.9181)
_add("sheikh-zayed", "الشيخ زايد", "Sheikh Zayed", 30.0136, 30.9780)
_add("10-ramadan", "10 رمضان", "10th of Ramadan", 30.2970, 31.7460)
_add("sadat", "مدينة السادات", "Sadat City", 30.3700, 30.5200)
_add("el-alamein", "العلمين", "El-Alamein", 30.8300, 28.9500)
_add("el-tor", "الطور", "El-Tor (Sinai)", 28.2410, 33.6220)
_add("abu-simbel", "أبو سمبل", "Abu Simbel", 22.3372, 31.6258)

DEFAULT_CITY = "cairo"

# Aliases users may type.
ALIASES: dict[str, str] = {
    "cairo": "cairo",
    "qahira": "cairo",
    "capital": "cairo",
    "alex": "alexandria",
    "eskan": "alexandria",
    "port said": "port-said",
    "portsaid": "port-said",
    "ismailiya": "ismailia",
    "el mansoura": "mansoura",
    "elmansoura": "mansoura",
    "zagzig": "zagazig",
    "kafr el sheikh": "kafr-elsheikh",
    "banha": "banha",
    "beni suef": "beni-suef",
    "el minya": "minya",
    "assiut": "asyut",
    "sharm el sheikh": "sharm",
    "sharm elsheikh": "sharm",
    "marsa matrouh": "matrouh",
    "matrouh": "matrouh",
    "kharga": "new-valley",
    "october": "6-october",
    "6 october": "6-october",
    "zayed": "sheikh-zayed",
    "new cairo": "new-cairo",
    "10th of ramadan": "10-ramadan",
    "el alamein": "el-alamein",
    "alamain": "el-alamein",
    "sinai": "el-tor",
    "hurghada": "hurghada",
    "luxor": "luxor",
    "aswan": "aswan",
}


def normalize(name: str) -> str:
    """Lowercase and turn separators into single spaces."""
    return " ".join(name.strip().lower().replace("-", " ").split())


def resolve(name: str | None) -> City | None:
    """Find a city by key, English name, Arabic name, or alias."""
    if not name:
        return None
    raw = name.strip().lower()
    if raw in CITIES:
        return CITIES[raw]
    norm = normalize(name)
    for city in CITIES.values():
        if norm in {normalize(city.name_en), city.name_ar.replace("ـ", "")}:
            return city
        if norm == normalize(city.name_en.replace("el-", "").replace("al-", "")):
            return city
    if norm in ALIASES:
        return CITIES.get(ALIASES[norm])
    for alias, key in ALIASES.items():
        if normalize(alias) == norm:
            return CITIES.get(key)
    # last resort: prefix match on the English name
    for city in CITIES.values():
        if normalize(city.name_en).startswith(norm):
            return city
    return None


def default_city() -> City:
    return CITIES[DEFAULT_CITY]
