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


class YearlyScraper:
    def __init__(self, league_type: str = "amateur"):
        self.league_type = league_type
        self.leagues = LEAGUES
        self.last_scrapes_path = Path(__file__).resolve().parent.parent / "runtime" / "last_scrapes.json"

    def load_runtime_state(self) -> dict:
        if not self.last_scrapes_path.exists():
            return {}

        with self.last_scrapes_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_runtime_state(self, state: dict) -> None:
        self.last_scrapes_path.parent.mkdir(parents=True, exist_ok=True)

        with self.last_scrapes_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)

    def get_saved_season(self) -> int:
        state = self.load_runtime_state()
        season = state.get("season")

        if season is None:
            raise KeyError("Key 'season' not found in runtime/last_scrapes.json")

        return int(season)

    def run(self) -> None:
        today = date.today()
        season = today.year if today.month >= 8 else today.year - 1

        print("[INFO] Yearly live run started")

        Path("data/scrape/amateur").mkdir(parents=True, exist_ok=True)

        scraper = ClubsScraper(
            league=LEAGUES,
            start_year=season,
            end_year=season + 1,
            league_type="amateur",
        )
        scraper.run()

        state = self.load_runtime_state()
        state["season"] = season
        self.save_runtime_state(state)

        ### Transform ###
        ### In DB einlesen ###
        ### CSV löschen ###

        print("[INFO] Yearly live run finished")


def get_saved_season() -> int:
    return YearlyScraper().get_saved_season()


def run_yearly() -> None:
    YearlyScraper().run()


if __name__ == "__main__":
    run_yearly()