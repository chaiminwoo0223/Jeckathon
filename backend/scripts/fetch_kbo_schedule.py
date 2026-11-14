"""Fetch a KBO season schedule from koreabaseball.com and write it as seed JSON.

One-off: the result is committed as app/seed/kbo_<season>.json and loaded by
init_db, so the app never calls the KBO site at runtime.

    cd backend && uv run python scripts/fetch_kbo_schedule.py 2026

Source: the schedule page's own endpoint (Schedule.asmx/GetScheduleList).
Each row is one game; the date cell only appears on the first game of a day.
The play cell reads "<away> <away score> vs <home score> <home>".
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; cheer101-seed/1.0)",
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}
# srIdList values used by the KBO schedule page
SERIES = {
    "regular": "0,9,6",  # regular season (incl. tie-breakers)
    "post": "3,4,5,7",  # wild card, semi-PO, PO, Korean Series
}
SEED_DIR = Path(__file__).resolve().parents[1] / "app" / "seed"

_TAG = re.compile(r"<[^>]+>")
_SPAN = re.compile(r"<span[^>]*>(.*?)</span>")
_DAY = re.compile(r"(\d{2})\.(\d{2})")
_ROUND = re.compile(r"^(WC|준PO|PO|KS) \d차전$")  # postseason labels in the note cell


def _text(html: str) -> str:
    return _TAG.sub("", html).strip()


def parse_rows(rows: list[dict], season: int, series: str) -> list[dict]:
    """Turn GetScheduleList rows into game dicts (cancelled games dropped)."""
    games: list[dict] = []
    day: str | None = None
    for row in rows:
        cells = row["row"]
        by_class = {c.get("Class"): c["Text"] for c in cells if c.get("Class")}
        if "day" in by_class:
            m = _DAY.search(by_class["day"])
            if m:
                day = f"{season}-{m.group(1)}-{m.group(2)}"
        if day is None or "play" not in by_class:
            continue

        note = _text(cells[-1]["Text"])
        spans = [_text(s) for s in _SPAN.findall(by_class["play"])]
        # finished: [away, a_score, "vs", h_score, home]; not played: [away, "vs", home]
        if len(spans) == 5:
            away, a_score, _, h_score, home = spans
            away_score, home_score = int(a_score), int(h_score)
        elif len(spans) == 3:
            away, _, home = spans
            away_score = home_score = None
            # no score + a reason (우천취소, 그라운드사정 ...) = cancelled
            if note not in ("", "-") and not _ROUND.match(note):
                continue
        else:
            continue

        clock = _text(by_class.get("time", "")) or "18:30"
        games.append(
            {
                "kickoff_at": f"{day}T{clock}:00+09:00",
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score,
                "venue": _text(cells[-2]["Text"]),
                "round_label": "" if note == "-" else note,
                "series": series,
            }
        )
    return games


def fetch_month(season: int, month: int, sr_ids: str) -> list[dict]:
    body = urllib.parse.urlencode(
        {
            "leId": "1",
            "srIdList": sr_ids,
            "seasonId": str(season),
            "gameMonth": f"{month:02d}",
            "teamId": "",
        }
    ).encode()
    req = urllib.request.Request(URL, data=body, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("rows", [])


def main() -> None:
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    games: list[dict] = []
    for series, sr_ids in SERIES.items():
        for month in range(3, 12):
            games += parse_rows(fetch_month(season, month, sr_ids), season, series)
            time.sleep(0.3)  # be gentle with the KBO site
    games.sort(key=lambda g: (g["kickoff_at"], g["home"]))

    SEED_DIR.mkdir(exist_ok=True)
    out = SEED_DIR / f"kbo_{season}.json"
    out.write_text(
        json.dumps({"season": season, "games": games}, ensure_ascii=False, indent=1)
        + "\n"
    )
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    print(f"{out}: {len(games)} games, teams={teams}")  # noqa: T201


if __name__ == "__main__":
    main()
