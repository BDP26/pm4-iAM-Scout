from __future__ import annotations

from pathlib import Path

import pandas as pd

from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.players import SofaScorePlayersParser


class SofaScorePlayersScraper:
    """Scraper for collecting player information from SofaScore."""

    DEFAULT_SEASON_URLS: dict[str, str] = {
        "25/26": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:77152,tab:stats",
        "24/25": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:61658,tab:stats",
        "23/24": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:52366,tab:stats",
        "22/23": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:42276,tab:stats",
        "21/22": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:37158,tab:stats",
        "20/21": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:32512,tab:stats"
    }

    def __init__(
        self,
        seasons: list[str] | None = None,
        client: SofaScoreClient | None = None,
    ) -> None:
        """Initialize SofaScore players scraper with seasons and client."""
        self.seasons = seasons or ["25/26", "24/25"]
        self.players_savepath = "data/scrape/pro/players_sofascore.csv"
        self.client = client or SofaScoreClient()
        self.parser = SofaScorePlayersParser()
        self.season_ids: dict[str, str] = dict(self.DEFAULT_SEASON_URLS)

    @staticmethod
    def _clean_id(value) -> str:
        """Clean and validate ID values from dataframes."""
        if value is None or pd.isna(value):
            return ""

        string_value = str(value).strip()
        if not string_value or string_value.lower() in {"nan", "<na>"}:
            return ""

        if string_value.endswith(".0"):
            string_value = string_value[:-2]

        return string_value

    def _save_players(self, players: pd.DataFrame) -> Path:
        """Save players dataframe to CSV file."""
        savepath = Path(self.players_savepath)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        players.to_csv(savepath, index=False)
        return savepath

    def _build_players_dataframe(self, player_index: dict[str, dict]) -> pd.DataFrame:
        """Build deduplicated players dataframe from player index."""
        if player_index:
            players = (
                pd.DataFrame(player_index.values())
                .drop_duplicates(subset=["id"])
                .sort_values(["name", "id"], na_position="last")
                .reset_index(drop=True)
            )
        else:
            players = pd.DataFrame(columns=["name", "id", "slug"])

        for column in ["name", "id", "slug"]:
            if column not in players.columns:
                players[column] = None

        return players[["name", "id", "slug"]]

    def _resolve_season_url(self, season: str) -> str:
        """Resolve season to full SofaScore stats URL."""
        if season not in self.season_ids:
            raise ValueError(
                f"Season '{season}' not found in season IDs. "
                f"Available: {list(self.season_ids.keys())}"
            )

        season_url = str(self.season_ids[season]).strip()
        if not season_url.startswith(("http://", "https://")):
            raise ValueError(
                f"season_ids[{season}] must be a complete SofaScore stats URL. "
                f"Got: {season_url}"
            )

        return season_url

    def run(self) -> pd.DataFrame:
        """Execute player scraping workflow for all seasons."""
        player_index: dict[str, dict] = {}

        try:
            for season_label in self.seasons:
                season_url = self._resolve_season_url(season_label)

                print(f"[INFO] Fetching stats pages for season {season_label}")

                try:
                    html_pages = self.client.get_stats_pages(season_url)
                except Exception as error:
                    print(
                        f"[WARN] stats pages failed: season={season_label}: {error}"
                    )
                    continue

                print(f"[INFO] Stats HTML pages fetched: {len(html_pages)}")

                all_parsed_rows: list[dict] = []

                for page_number, html in enumerate(html_pages, start=1):
                    parsed_rows = self.parser.parse_players_from_stats_page(html)
                    print(
                        f"[INFO] Parsed page {page_number}: {len(parsed_rows)} players "
                        f"for season {season_label}"
                    )
                    all_parsed_rows.extend(parsed_rows)

                deduplicated: dict[str, dict] = {}
                for row in all_parsed_rows:
                    player_id = self._clean_id(row.get("id"))
                    if not player_id:
                        continue

                    if player_id not in deduplicated:
                        deduplicated[player_id] = {
                            "id": player_id,
                            "name": row.get("name"),
                            "slug": row.get("slug"),
                        }

                print(f"[INFO] Deduplicated rows total: {len(deduplicated)}")

                for player_id, row in deduplicated.items():
                    if player_id not in player_index:
                        player_index[player_id] = {
                            "id": player_id,
                            "name": row.get("name"),
                            "slug": row.get("slug"),
                        }
                    else:
                        if not player_index[player_id].get("name") and row.get("name"):
                            player_index[player_id]["name"] = row.get("name")
                        if not player_index[player_id].get("slug") and row.get("slug"):
                            player_index[player_id]["slug"] = row.get("slug")

            print(f"[INFO] Total unique players to enrich: {len(player_index)}")

            for index, (player_id, base_info) in enumerate(player_index.items(), start=1):
                if index % 50 == 0 or index == len(player_index):
                    print(f"[INFO] Profiles progress: {index}/{len(player_index)}")

                slug = (base_info.get("slug") or "").strip()
                if not slug:
                    continue

                try:
                    html = self.client.get_player_profile(slug, player_id)
                    parsed_profile = self.parser.parse_player_profile(html)

                    if parsed_profile and parsed_profile.get("canonical_slug"):
                        base_info["slug"] = parsed_profile["canonical_slug"]
                except Exception as error:
                    print(f"[WARN] player profile failed: player_id={player_id}, slug={slug}")

        finally:
            self.client.close()

        players = self._build_players_dataframe(player_index)
        savepath = self._save_players(players)
        print(f"[INFO] Players saved to: {savepath}")

        return players

