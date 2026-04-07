from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from web_scraping.transfermarkt.scraper.clubs import ClubsScraper


LEAGUES = [
    "pl",
    "1_liga_gr_1",
    "1_liga_gr_2",
    "1_liga_gr_3",
]

LAST_SCRAPES_PATH = "../runtime/last_scrapes.json"


def _load_runtime_state() -> dict:
    if not LAST_SCRAPES_PATH.exists():
        return {}

    with LAST_SCRAPES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_runtime_state(state: dict) -> None:
    LAST_SCRAPES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LAST_SCRAPES_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def get_saved_season() -> int:
    state = _load_runtime_state()
    season = state.get("season")
    if season is None:
        raise KeyError("Key 'season' not found in runtime/last_scrapes.json")
    return int(season)


def run_yearly() -> None:
    date_today = date.today()
    season = date_today.year

    print("[INFO] Yearly live run started")

    scraper = ClubsScraper(
        league=LEAGUES,
        start_year=season,
        end_year=season + 1,
        league_type="amateur",
    )
    scraper.run()

    state = _load_runtime_state()
    state["season"] = season
    _save_runtime_state(state)

    print("[INFO] Yearly live run finished")