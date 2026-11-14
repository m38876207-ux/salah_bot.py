"""
Compare the local calculation engine against the AlAdhan API.

Usage:
    python -m scripts.verify_times [--days 30] [--no-network]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from salahbot.cities import CITIES  # noqa: E402
from salahbot.prayer_times import METHODS, calculate_times  # noqa: E402

API = "https://api.aladhan.com/v1/timings/{day}-{month}-{year}"

METHOD_IDS = {
    "egypt": 5,
    "mwl": 3,
    "isna": 2,
    "umm_al_qura": 4,
    "karachi": 1,
}

KEYS = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
ADHAN_KEYS = {
    "fajr": "Fajr",
    "sunrise": "Sunrise",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "maghrib": "Maghrib",
    "isha": "Isha",
}


def fetch(city_key: str, day: date, method_key: str) -> dict[str, str]:
    city = CITIES[city_key]
    url = (
        f"{API.format(day=day.day, month=day.month, year=day.year)}"
        f"?latitude={city.latitude}&longitude={city.longitude}"
        f"&method={METHOD_IDS.get(method_key, 5)}&school=0"
    )
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.load(resp)
    return payload["data"]["timings"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--city", default="cairo")
    parser.add_argument("--method", default="egypt")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument(
        "--city-key",
        default=None,
        help="iterate over these comma separated cities (default: a few)",
    )
    args = parser.parse_args()

    city_keys = args.city_key.split(",") if args.city_key else [args.city]
    start = date.today()
    worst: dict[str, int] = {}
    rows: list[str] = []

    for city_key in city_keys:
        city = CITIES[city_key]
        for offset in range(args.days):
            day = start + timedelta(days=offset)
            local = calculate_times(
                latitude=city.latitude,
                longitude=city.longitude,
                timezone=city.timezone,
                day=day,
                method=args.method,
            )
            if args.no_network:
                continue
            try:
                remote = fetch(city_key, day, args.method)
            except Exception as exc:  # noqa: BLE001
                print(f"network error: {exc}")
                return 2
            for key in KEYS:
                local_hh, local_mm = local[key].strftime("%H:%M").split(":")
                remote_hh, remote_mm = remote[ADHAN_KEYS[key]].split(" ")[0].split(":")
                lhs = int(local_hh) * 60 + int(local_mm)
                rhs = int(remote_hh) * 60 + int(remote_mm)
                diff = (lhs - rhs) * 60  # seconds
                current = worst.get(key)
                if current is None or abs(diff) > abs(current):
                    worst[key] = diff
                    rows.append(
                        f"{city.name_en:<14} {day} {key:<8} "
                        f"local={local_hh}:{local_mm} api={remote_hh}:{remote_mm} "
                        f"diff={diff:+d}s"
                    )

    if args.no_network:
        city = CITIES[city_keys[0]]
        day = date.today()
        local = calculate_times(
            latitude=city.latitude,
            longitude=city.longitude,
            timezone=city.timezone,
            day=day,
            method=args.method,
        )
        for key in KEYS:
            print(f"{key:<8} {local[key].strftime('%H:%M')}")

    if rows:
        print("\n".join(rows[-12:]))
    if worst:
        print("\nworst deltas (seconds):")
        for key in KEYS:
            print(f"  {key:<8} {worst.get(key, 0):+d}")
        total = sum(abs(v) for v in worst.values())
        print(f"  total    {total}s  ->  {'OK' if all(abs(v) < 120 for v in worst.values()) else 'CHECK'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
