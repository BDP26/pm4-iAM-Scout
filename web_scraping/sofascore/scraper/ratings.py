from __future__ import annotations

from pathlib import Path

import pandas as pd

from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.ratings import SofaScorePlayerStatsParser


class SofaScorePlayerStatsScraper:
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
    def _clean_str(x) -> str:
        if x is None or pd.isna(x):
            return ""
        return str(x).strip()

    def _load_players(self) -> pd.DataFrame:
        path = Path(self.players_path)
        if not path.exists():
            raise FileNotFoundError(f"players csv nicht gefunden: {path}")

        players = pd.read_csv(path, dtype=str).fillna("")

        required_cols = ["name", "id", "slug"]
        missing = [c for c in required_cols if c not in players.columns]
        if missing:
            raise ValueError(
                f"players csv hat nicht die erwarteten Spalten. "
                f"Fehlt: {missing}. Erwartet: {required_cols}"
            )

        return players[required_cols].copy()

    def _save(self, df: pd.DataFrame) -> Path:
        savepath = Path(self.player_stats_savepath)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(savepath, index=False)
        return savepath

    def _reset_client(self) -> None:
        if not self._owns_client:
            return

        try:
            self.client.close()
        except Exception:
            pass

        self.client = SofaScoreClient()

    def _parse_pages_for_player(self, html_pages: list[str], player_name: str) -> list[dict]:
        rows: list[dict] = []

        for page_no, html in enumerate(html_pages, start=1):
            page_rows = self.parser.parse_player_matches(
                html=html,
                player_name=player_name,
                min_date=self.min_date,
            )
            print(f"[DEBUG] Parsed page {page_no}: {len(page_rows)} rows for {player_name}")
            rows.extend(page_rows)

        if not rows:
            return []

        df = (
            pd.DataFrame(rows)
            .drop_duplicates(subset=["name", "datum", "rating"])
            .sort_values(["name", "datum"], na_position="last")
            .reset_index(drop=True)
        )
        return df.to_dict("records")

    def _flush_batch_to_csv(self, rows: list[dict]) -> None:
        if not rows:
            print("[INFO] Batch save skipped: no rows")
            return

        new_df = pd.DataFrame(rows)

        if Path(self.player_stats_savepath).exists():
            existing_df = pd.read_csv(self.player_stats_savepath)
        else:
            existing_df = pd.DataFrame(columns=["name", "datum", "rating"])

        out_df = pd.concat([existing_df, new_df], ignore_index=True)

        if not out_df.empty:
            out_df = (
                out_df.drop_duplicates(subset=["name", "datum", "rating"])
                .sort_values(["name", "datum"], na_position="last")
                .reset_index(drop=True)
            )

        self._save(out_df)
        print(
            f"[INFO] Batch saved to {self.player_stats_savepath}: "
            f"+{len(new_df)} raw rows, total={len(out_df)}"
        )

    def run(self) -> pd.DataFrame:
        players = self._load_players()

        batch_rows: list[dict] = []
        processed_with_current_client = 0
        processed_since_last_save = 0

        try:
            total = len(players)

            for i, row in players.iterrows():
                if self._owns_client and processed_with_current_client >= self.client_reset_every:
                    print(f"[INFO] Reset client after {processed_with_current_client} players")
                    self._reset_client()
                    processed_with_current_client = 0

                name = self._clean_str(row.get("name"))
                player_id = self._clean_str(row.get("id"))
                slug = self._clean_str(row.get("slug"))

                if not player_id or not slug:
                    print(f"[WARN] skip row={i}: fehlende id oder slug")
                    processed_with_current_client += 1
                    processed_since_last_save += 1

                    if processed_since_last_save >= self.save_every_players:
                        self._flush_batch_to_csv(batch_rows)
                        batch_rows = []
                        processed_since_last_save = 0

                    continue

                print(
                    f"[INFO] Player {i + 1}/{total}: {name} "
                    f"(id={player_id}, slug={slug})"
                )

                try:
                    html_pages = self.client.get_player_match_history_pages(
                        player_slug=slug,
                        player_id=player_id,
                        competition=self.competition,
                        min_date=self.min_date,
                    )
                    print(f"[DEBUG] Collected pages for {name}: {len(html_pages)}")

                    parsed_rows = self._parse_pages_for_player(
                        html_pages=html_pages,
                        player_name=name,
                    )
                    print(f"[INFO] Parsed matches for {name}: {len(parsed_rows)}")

                    batch_rows.extend(parsed_rows)

                except Exception as e:
                    print(
                        f"[WARN] player stats failed: "
                        f"name={name}, id={player_id}, slug={slug}: {e}"
                    )

                processed_with_current_client += 1
                processed_since_last_save += 1

                if processed_since_last_save >= self.save_every_players:
                    self._flush_batch_to_csv(batch_rows)
                    batch_rows = []
                    processed_since_last_save = 0

            self._flush_batch_to_csv(batch_rows)

        finally:
            try:
                self.client.close()
            except Exception:
                pass

        if Path(self.player_stats_savepath).exists():
            df = pd.read_csv(self.player_stats_savepath)
        else:
            df = pd.DataFrame(columns=["name", "datum", "rating"])

        for col in ["name", "datum", "rating"]:
            if col not in df.columns:
                df[col] = None

        df = df[["name", "datum", "rating"]]
        print(f"Saved: {self.player_stats_savepath}")

        return df


def main() -> None:
    scraper = SofaScorePlayerStatsScraper(
        min_date="2024-01-01",
        client_reset_every=20,
        save_every_players=20,
    )
    scraper.run()


if __name__ == "__main__":
    main()