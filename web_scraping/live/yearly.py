"""
Yearly Live Data Scraping and Update

This module orchestrates yearly updates of team and league data by:
- Scraping all clubs for new seasons
- Checking for new seasons to track
- Running the full live transformation and ML pipeline
- Initializing seasonal data structures

Main functions:
- run_yearly_update(): Execute complete yearly data update process
- get_saved_season(): Retrieve saved season information from storage
"""

from __future__ import annotations

import json
from datetime import date
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from web_scraping.toolkit.live_t_l import main as run_live_tl
from web_scraping.transfermarkt.scraper.clubs import ClubsScraper


LEAGUES = [
    "pl",
    "1_liga_gr_1",
    "1_liga_gr_2",
    "1_liga_gr_3",
]

DEFAULT_LEAGUE_TYPE = "amateur"
SEASON_START_MONTH = 8
RUNTIME_STATE_PATH = Path("web_scraping") / "runtime" / "last_scrapes.json"


class YearlyScraper:
    """Run the yearly live scraping process for seasonal club data."""

    def __init__(
        self,
        project_root: Path | None = None,
        league_type: str = DEFAULT_LEAGUE_TYPE,
    ) -> None:
        """Initialize paths and configuration for the yearly scraper."""
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.league_type = league_type
        self.leagues = LEAGUES
        self.last_scrapes_path = self.project_root / RUNTIME_STATE_PATH
        self.data_dir = self.project_root / "data" / "scrape" / self.league_type

    def load_runtime_state(self) -> dict[str, Any]:
        """Load the stored runtime state from the last scrapes file."""
        if not self.last_scrapes_path.exists():
            return {}

        try:
            with self.last_scrapes_path.open("r", encoding="utf-8") as runtime_file:
                return json.load(runtime_file)
        except JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON in runtime state file: {self.last_scrapes_path}"
            ) from error

    def save_runtime_state(self, runtime_state: dict[str, Any]) -> None:
        """Save the runtime state to the last scrapes file."""
        self.last_scrapes_path.parent.mkdir(parents=True, exist_ok=True)

        with self.last_scrapes_path.open("w", encoding="utf-8") as runtime_file:
            json.dump(runtime_state, runtime_file, indent=4, ensure_ascii=False)

    @staticmethod
    def get_current_season(reference_date: date | None = None) -> int:
        """Return the football season start year for a given date."""
        current_date = reference_date or date.today()

        if current_date.month >= SEASON_START_MONTH:
            return current_date.year

        return current_date.year - 1

    def get_saved_season(self) -> int:
        """Return the latest saved season from the runtime state."""
        runtime_state = self.load_runtime_state()
        season = runtime_state.get("season")

        if season is None:
            raise KeyError("Key 'season' not found in runtime/last_scrapes.json")

        return int(season)

    def scrape_clubs(self, season: int) -> None:
        """Scrape club data for the selected season."""
        scraper = ClubsScraper(
            league=self.leagues,
            start_year=season,
            end_year=season + 1,
            league_type=self.league_type,
        )
        scraper.run()

    def update_saved_season(self, season: int) -> None:
        """Store the current season in the runtime state."""
        runtime_state = self.load_runtime_state()
        runtime_state["season"] = season
        self.save_runtime_state(runtime_state)

    def run(self) -> None:
        """Run the yearly live scraping workflow."""
        season = self.get_current_season()

        print("[INFO] Yearly live run started")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.scrape_clubs(season)
        self.update_saved_season(season)

        print("[INFO] Yearly live run finished")


def get_saved_season() -> int:
    """Return the latest saved season from the yearly scraper state."""
    return YearlyScraper().get_saved_season()


def run_yearly() -> None:
    """Run the yearly live scraping workflow."""
    YearlyScraper().run()


def main() -> None:
    """Run yearly scraping followed by transform, rating prediction and loading."""
    run_yearly()
    run_live_tl()


if __name__ == "__main__":
    main()
