from __future__ import annotations

import time
from typing import Any

import requests

from web_scraping.config import PRO_TOURNAMENT_ID, SLEEP_SECONDS


class SofaScoreClient:
    BASE_API_URL = "https://www.sofascore.com/api/v1"

    def __init__(self, sleep_seconds: float = SLEEP_SECONDS) -> None:
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.sofascore.com/",
            }
        )

    def get_json(self, url: str) -> dict[str, Any]:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        time.sleep(self.sleep_seconds)
        return response.json()

    def get_standings(
        self,
        season_id: int,
        unique_tournament_id: int = PRO_TOURNAMENT_ID,
    ) -> dict[str, Any]:
        url = (
            f"{self.BASE_API_URL}/unique-tournament/"
            f"{unique_tournament_id}/season/{season_id}/standings/total"
        )
        return self.get_json(url)

    def get_team_players(self, team_id: int | str) -> dict[str, Any]:
        url = f"{self.BASE_API_URL}/team/{team_id}/players"
        return self.get_json(url)

    def get_player(self, player_id: int | str) -> dict[str, Any]:
        url = f"{self.BASE_API_URL}/player/{player_id}"
        return self.get_json(url)