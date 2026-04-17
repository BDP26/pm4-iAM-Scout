from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from web_scraping.live.yearly import LEAGUES, get_saved_season
from web_scraping.toolkit.live_t_l import main as run_live_tl
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper
from web_scraping.transfermarkt.scraper.players import PlayersScraper


class WeeklyAmateurScraper:
    def __init__(
        self,
        project_root: Path | None = None,
        db_url: str = "postgresql+psycopg2://postgres:postgres@host.docker.internal:5434/iamscout",
        league_type: str = "amateur",
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.db_url = db_url
        self.league_type = league_type

        self.data_dir = self.project_root / "data" / "scrape" / self.league_type
        self.last_scrapes_path = (
            self.project_root / "web_scraping" / "runtime" / "last_scrapes.json"
        )

        self.matches_savepath = self.data_dir / "matches.csv"
        self.player_stats_savepath = self.data_dir / "player_stats.csv"
        self.players_savepath = self.data_dir / "players.csv"
        self.squads_savepath = self.data_dir / "squads.csv"

        self.engine: Engine = create_engine(self.db_url)

    def _load_last_scrape_match_date(self) -> date:
        if not self.last_scrapes_path.exists():
            raise FileNotFoundError(
                f"last_scrapes.json not found: {self.last_scrapes_path}"
            )

        with self.last_scrapes_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        last_scrape_match = data.get("matches")
        if not last_scrape_match:
            raise KeyError("Key 'matches' not found in last_scrapes.json")

        return datetime.strptime(last_scrape_match, "%d.%m.%y %H:%M:%S").date()

    def _empty_player_stats_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "player_id",
                "match_id",
                "club_id",
                "goals",
                "assists",
                "yellow",
                "yellow_red",
                "red",
                "start_eleven",
                "minutes",
                "on_min",
                "off_min",
                "team_goals",
                "team_conceded",
            ]
        )

    def _empty_players_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "nationality",
                "date_of_birth",
                "height",
                "position",
                "player_slug",
            ]
        )

    def _empty_squads_df(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["player_id", "club_id", "season"])

    def _filter_matches_csv(
        self,
        matches_path: Path,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        if not matches_path.exists():
            raise FileNotFoundError(f"matches.csv not found: {matches_path}")

        df = pd.read_csv(
            matches_path,
            dtype={
                "match_id": "string",
                "season": "Int64",
                "league": "string",
                "date": "string",
                "home_club_id": "string",
                "away_club_id": "string",
                "home_goals": "Int64",
                "away_goals": "Int64",
                "matches_slug": "string",
            },
        )

        if df.empty:
            print("[INFO] matches.csv is empty, nothing to filter")
            matches_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(matches_path, index=False, encoding="utf-8-sig")
            return df

        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["match_id"] = df["match_id"].astype("string").str.strip()
        df["matches_slug"] = df["matches_slug"].astype("string").str.strip()

        df = df[
            df["date"].notna()
            & (df["date"] >= start_date)
            & (df["date"] <= end_date)
            & df["home_goals"].notna()
            & df["away_goals"].notna()
            & df["match_id"].notna()
            & (df["match_id"] != "")
            & df["matches_slug"].notna()
            & (df["matches_slug"] != "")
            & (df["matches_slug"].str.lower() != "nan")
            & (df["matches_slug"].str.lower() != "<na>")
        ].copy()

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        matches_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(matches_path, index=False, encoding="utf-8-sig")

        print(f"[INFO] Filtered matches saved to: {matches_path}")
        print(
            f"[INFO] Finished matches kept between {start_date} and {end_date}: {len(df)}"
        )

        return df

    @staticmethod
    def season_to_db(current_season: int) -> str:
        current_season = int(current_season)
        return f"{str(current_season)[-2:]}/{str(current_season + 1)[-2:]}"

    def _get_db_player_ids(self) -> set[str]:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT player_id FROM players"))
            return {str(row[0]).strip() for row in result if row[0] is not None}

    def _save_player_stats(self, player_stats: pd.DataFrame) -> None:
        self.player_stats_savepath.parent.mkdir(parents=True, exist_ok=True)
        player_stats.to_csv(self.player_stats_savepath, index=False, encoding="utf-8-sig")
        print(f"[INFO] player_stats saved to: {self.player_stats_savepath}")

    def _save_players(self, players: pd.DataFrame) -> None:
        self.players_savepath.parent.mkdir(parents=True, exist_ok=True)
        players.to_csv(self.players_savepath, index=False, encoding="utf-8-sig")
        print(f"[INFO] players saved to: {self.players_savepath}")

    def _build_missing_squads(
        self,
        player_stats: pd.DataFrame,
        db_season: str,
        valid_player_ids: set[str],
    ) -> pd.DataFrame:
        squad_candidates = player_stats[["player_id", "club_id"]].dropna().copy()

        if squad_candidates.empty:
            return self._empty_squads_df()

        squad_candidates["player_id"] = (
            squad_candidates["player_id"].astype(str).str.strip()
        )
        squad_candidates["club_id"] = (
            squad_candidates["club_id"].astype(str).str.strip()
        )
        squad_candidates["season"] = db_season

        squad_candidates = squad_candidates[
            squad_candidates["player_id"].isin(valid_player_ids)
        ][["player_id", "club_id", "season"]].drop_duplicates()

        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT player_id, club_id, season
                    FROM squads
                    """
                )
            )
            existing_squads = {
                (str(row[0]).strip(), str(row[1]).strip(), str(row[2]).strip())
                for row in result
            }

        missing_squads = [
            (row["player_id"], row["club_id"], row["season"])
            for _, row in squad_candidates.iterrows()
            if (row["player_id"], row["club_id"], row["season"]) not in existing_squads
        ]

        return pd.DataFrame(missing_squads, columns=["player_id", "club_id", "season"])

    def _save_squads(self, squads_df: pd.DataFrame) -> None:
        self.squads_savepath.parent.mkdir(parents=True, exist_ok=True)
        squads_df.to_csv(self.squads_savepath, index=False, encoding="utf-8-sig")
        print(f"[INFO] squads saved to: {self.squads_savepath}")
        print(f"[INFO] Missing squads saved: {len(squads_df)}")

    def run(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

        season = get_saved_season()
        date_today = date.today()
        start_date = self._load_last_scrape_match_date()
        end_date = date_today

        print("[INFO] Weekly live run started")

        if start_date > end_date:
            print("[INFO] Weekly window is empty")
            self._save_player_stats(self._empty_player_stats_df())
            self._save_players(self._empty_players_df())
            self._save_squads(self._empty_squads_df())
            print("[INFO] Weekly live run finished")
            return

        matches_scraper = MatchesScraper(
            league=LEAGUES,
            start_year=season,
            end_year=season + 1,
            league_type=self.league_type,
        )
        matches_scraper.run()

        matches_path = Path(matches_scraper.matches_savepath)
        filtered_matches = self._filter_matches_csv(
            matches_path=matches_path,
            start_date=start_date,
            end_date=end_date,
        )

        if filtered_matches.empty:
            print("[INFO] No finished matches in weekly window")
            self._save_player_stats(self._empty_player_stats_df())
            self._save_players(self._empty_players_df())
            self._save_squads(self._empty_squads_df())
            print("[INFO] Weekly live run finished")
            return

        player_stats_scraper = PlayerStatsScraper(league_type=self.league_type)
        player_stats = player_stats_scraper.run()

        if player_stats.empty:
            print("[WARN] No player_stats scraped for current weekly window")

        unique_player_ids = (
            player_stats["player_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        db_player_ids = self._get_db_player_ids()
        missing_player_ids = [
            player_id for player_id in unique_player_ids if player_id not in db_player_ids
        ]

        print(f"[INFO] Unique players to fetch: {len(missing_player_ids)}")

        if missing_player_ids:
            player_scraper = PlayersScraper(league_type=self.league_type)
            players = player_scraper.scrape_players_by_ids(missing_player_ids)
        else:
            players = self._empty_players_df()

        self._save_players(players)

        new_player_ids: set[str] = set()
        if not players.empty and "player_id" in players.columns:
            new_player_ids = set(
                players["player_id"]
                .dropna()
                .astype(str)
                .str.strip()
                .tolist()
            )

        valid_player_ids = db_player_ids | new_player_ids

        db_season = self.season_to_db(season)
        squads_df = self._build_missing_squads(
            player_stats=player_stats,
            db_season=db_season,
            valid_player_ids=valid_player_ids,
        )
        self._save_squads(squads_df)

        print("[INFO] Weekly live run finished")

    def close(self) -> None:
        self.engine.dispose()


def run_weekly() -> None:
    scraper = WeeklyAmateurScraper()
    try:
        scraper.run()
    finally:
        scraper.close()


def main() -> None:
    run_weekly()
    run_live_tl()


if __name__ == "__main__":
    main()