from __future__ import annotations

from pathlib import Path

import pandas as pd

from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.ratings import SofaScorePlayerStatsParser


class SofaScorePlayerStatsScraper:
    """Scraper for collecting player match statistics and ratings from SofaScore."""

    def __init__(
        self,
        players_path: str = "data/scrape/pro/players_sofascore.csv",
        savepath: str = "data/scrape/pro/ratings.csv",
        competition: str = "Swiss Super League",
        min_date: str = "2024-07-01",
        client: SofaScoreClient | None = None,
        client_reset_every: int = 20,
        save_every_players: int = 20,
    ) -> None:
        """Initialize SofaScore player stats scraper with configuration."""
        self.players_path = players_path
        self.player_stats_savepath = savepath
        self.competition = competition
        self.min_date = min_date
        self.client = client or SofaScoreClient()
        self.parser = SofaScorePlayerStatsParser()
        self.client_reset_every = client_reset_every
        self.save_every_players = save_every_players
        self._owns_client = client is None

    @staticmethod
    def _clean_string(value) -> str:
        """Clean string values from dataframes."""
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    def _load_players(self) -> pd.DataFrame:
        """Load players dataframe from CSV file."""
        path = Path(self.players_path)
        if not path.exists():
            raise FileNotFoundError(f"players CSV not found: {path}")

        players = pd.read_csv(path, dtype=str).fillna("")

        required_columns = ["name", "id", "slug"]
        missing_columns = [col for col in required_columns if col not in players.columns]
        if missing_columns:
            raise ValueError(
                f"players CSV missing expected columns: {missing_columns}. "
                f"Required: {required_columns}"
            )

        return players[required_columns].copy()

    def _save(self, dataframe: pd.DataFrame) -> Path:
        """Save dataframe to CSV file."""
        savepath = Path(self.player_stats_savepath)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(savepath, index=False)
        return savepath

    def _reset_client(self) -> None:
        """Reset browser client connection."""
        if not self._owns_client:
            return

        try:
            self.client.close()
        except Exception:
            pass

        self.client = SofaScoreClient()

    def _parse_player_match_history(self, html_pages: list[str], player_name: str) -> list[dict]:
        """Parse player match history from HTML pages."""
        rows: list[dict] = []

        for page_number, html in enumerate(html_pages, start=1):
            page_rows = self.parser.parse_player_matches(
                html=html,
                player_name=player_name,
                min_date=self.min_date,
            )
            print(f"[DEBUG] Page {page_number}: {len(page_rows)} rows for {player_name}")
            rows.extend(page_rows)

        if not rows:
            return []

        dataframe = (
            pd.DataFrame(rows)
            .drop_duplicates(subset=["name", "datum", "rating"])
            .sort_values(["name", "datum"], na_position="last")
            .reset_index(drop=True)
        )
        return dataframe.to_dict("records")

    def _save_batch_to_csv(self, rows: list[dict]) -> None:
        """Save batch of rows to CSV with deduplication."""
        if not rows:
            print("[INFO] Batch save skipped: no rows")
            return

        new_dataframe = pd.DataFrame(rows)

        if Path(self.player_stats_savepath).exists():
            existing_dataframe = pd.read_csv(self.player_stats_savepath)
        else:
            existing_dataframe = pd.DataFrame(columns=["name", "datum", "rating"])

        output_dataframe = pd.concat([existing_dataframe, new_dataframe], ignore_index=True)

        if not output_dataframe.empty:
            output_dataframe = (
                output_dataframe.drop_duplicates(subset=["name", "datum", "rating"])
                .sort_values(["name", "datum"], na_position="last")
                .reset_index(drop=True)
            )

        self._save(output_dataframe)
        print(
            f"[INFO] Batch saved: +{len(new_dataframe)} rows, "
            f"total={len(output_dataframe)}"
        )

    def run(self) -> pd.DataFrame:
        """Execute player stats scraping workflow."""
        players = self._load_players()

        batch_rows: list[dict] = []
        processed_with_current_client = 0
        processed_since_last_save = 0

        try:
            total_players = len(players)

            for row_index, player_row in players.iterrows():
                if self._owns_client and processed_with_current_client >= self.client_reset_every:
                    print(
                        f"[INFO] Reset client after {processed_with_current_client} players"
                    )
                    self._reset_client()
                    processed_with_current_client = 0

                player_name = self._clean_string(player_row.get("name"))
                player_id = self._clean_string(player_row.get("id"))
                player_slug = self._clean_string(player_row.get("slug"))

                if not player_id or not player_slug:
                    print(f"[WARN] Skip row {row_index}: missing id or slug")
                    processed_with_current_client += 1
                    processed_since_last_save += 1

                    if processed_since_last_save >= self.save_every_players:
                        self._save_batch_to_csv(batch_rows)
                        batch_rows = []
                        processed_since_last_save = 0

                    continue

                print(f"[INFO] Player {row_index + 1}/{total_players}: {player_name}")

                try:
                    html_pages = self.client.get_player_match_history_pages(
                        player_slug=player_slug,
                        player_id=player_id,
                        competition=self.competition,
                        min_date=self.min_date,
                    )
                    print(f"[DEBUG] Collected {len(html_pages)} pages for {player_name}")

                    parsed_rows = self._parse_player_match_history(
                        html_pages=html_pages,
                        player_name=player_name,
                    )
                    print(f"[INFO] Parsed {len(parsed_rows)} matches for {player_name}")

                    batch_rows.extend(parsed_rows)

                except Exception as error:
                    print(
                        f"[WARN] player stats failed: "
                        f"name={player_name}, id={player_id}, slug={player_slug}"
                    )

                processed_with_current_client += 1
                processed_since_last_save += 1

                if processed_since_last_save >= self.save_every_players:
                    self._save_batch_to_csv(batch_rows)
                    batch_rows = []
                    processed_since_last_save = 0

            self._save_batch_to_csv(batch_rows)

        finally:
            try:
                self.client.close()
            except Exception:
                pass

        if Path(self.player_stats_savepath).exists():
            result_dataframe = pd.read_csv(self.player_stats_savepath)
        else:
            result_dataframe = pd.DataFrame(columns=["name", "datum", "rating"])

        for column in ["name", "datum", "rating"]:
            if column not in result_dataframe.columns:
                result_dataframe[column] = None

        result_dataframe = result_dataframe[["name", "datum", "rating"]]
        print(f"[INFO] Player stats saved to: {self.player_stats_savepath}")

        return result_dataframe

