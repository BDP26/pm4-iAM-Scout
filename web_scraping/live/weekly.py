"""
Weekly Live Data Scraping and Update

This module orchestrates weekly updates of player statistics and match data by:
- Scraping the latest player statistics from matches
- Tracking last scrape dates to avoid redundant data collection
- Running the full live transformation and ML pipeline
- Updating the database with new ratings and recommendations

Main functions:
- run_weekly_update(): Execute complete weekly data update process
"""

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


DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@host.docker.internal:5434/iamscout"
LAST_SCRAPE_DATE_FORMAT = "%d.%m.%y %H:%M:%S"
CSV_ENCODING = "utf-8-sig"

PLAYER_STATS_COLUMNS = [
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

PLAYER_COLUMNS = [
    "player_id",
    "player_name",
    "nationality",
    "date_of_birth",
    "height",
    "position",
    "player_slug",
]

SQUAD_COLUMNS = [
    "player_id",
    "club_id",
    "season",
]

MATCH_DTYPES = {
    "match_id": "string",
    "season": "Int64",
    "league": "string",
    "date": "string",
    "home_club_id": "string",
    "away_club_id": "string",
    "home_goals": "Int64",
    "away_goals": "Int64",
    "matches_slug": "string",
}


class WeeklyAmateurScraper:
    """Scrape weekly amateur matches, player statistics, missing players, and squads."""

    def __init__(
        self,
        project_root: Path | None = None,
        db_url: str = DEFAULT_DB_URL,
        league_type: str = "amateur",
    ) -> None:
        """Initialize paths, database connection, and scraper configuration."""
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
        """Load the last scraped match date from the runtime state file."""
        if not self.last_scrapes_path.exists():
            raise FileNotFoundError(
                f"last_scrapes.json not found: {self.last_scrapes_path}"
            )

        with self.last_scrapes_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        last_scrape_match = data.get("matches")
        if not last_scrape_match:
            raise KeyError("Key 'matches' not found in last_scrapes.json")

        return datetime.strptime(last_scrape_match, LAST_SCRAPE_DATE_FORMAT).date()

    @staticmethod
    def _empty_player_stats_dataframe() -> pd.DataFrame:
        """Return an empty player statistics dataframe with the expected schema."""
        return pd.DataFrame(columns=PLAYER_STATS_COLUMNS)

    @staticmethod
    def _empty_players_dataframe() -> pd.DataFrame:
        """Return an empty players dataframe with the expected schema."""
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    @staticmethod
    def _empty_squads_dataframe() -> pd.DataFrame:
        """Return an empty squads dataframe with the expected schema."""
        return pd.DataFrame(columns=SQUAD_COLUMNS)

    @staticmethod
    def season_to_db(current_season: int) -> str:
        """Convert a season start year to the database season format."""
        current_season = int(current_season)
        return f"{str(current_season)[-2:]}/{str(current_season + 1)[-2:]}"

    @staticmethod
    def _normalize_identifier_series(series: pd.Series) -> pd.Series:
        """Normalize identifier values to stripped strings."""
        return series.dropna().astype(str).str.strip()

    def _filter_matches_csv(
        self,
        matches_path: Path,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Filter the scraped matches file to finished matches in the weekly window."""
        if not matches_path.exists():
            raise FileNotFoundError(f"matches.csv not found: {matches_path}")

        matches = pd.read_csv(matches_path, dtype=MATCH_DTYPES)

        if matches.empty:
            print("[INFO] matches.csv is empty, nothing to filter")
            self._write_dataframe(matches, matches_path)
            return matches

        matches["date"] = pd.to_datetime(matches["date"], errors="coerce").dt.date
        matches["match_id"] = matches["match_id"].astype("string").str.strip()
        matches["matches_slug"] = matches["matches_slug"].astype("string").str.strip()

        valid_matches = matches[
            matches["date"].notna()
            & (matches["date"] >= start_date)
            & (matches["date"] <= end_date)
            & matches["home_goals"].notna()
            & matches["away_goals"].notna()
            & matches["match_id"].notna()
            & (matches["match_id"] != "")
            & matches["matches_slug"].notna()
            & (matches["matches_slug"] != "")
            & (matches["matches_slug"].str.lower() != "nan")
            & (matches["matches_slug"].str.lower() != "<na>")
        ].copy()

        if not valid_matches.empty:
            valid_matches["date"] = pd.to_datetime(valid_matches["date"]).dt.strftime(
                "%Y-%m-%d"
            )

        self._write_dataframe(valid_matches, matches_path)
        print(f"[INFO] Filtered matches saved to: {matches_path}")
        print(
            f"[INFO] Finished matches kept between {start_date} and {end_date}: "
            f"{len(valid_matches)}"
        )

        return valid_matches

    def _get_db_player_ids(self) -> set[str]:
        """Load all existing player identifiers from the database."""
        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT player_id FROM players"))
            return {str(row[0]).strip() for row in result if row[0] is not None}

    def _get_existing_squads(self) -> pd.DataFrame:
        """Load existing squads from the database."""
        query = text("SELECT player_id, club_id, season FROM squads")

        with self.engine.connect() as connection:
            squads = pd.read_sql_query(query, connection)

        if squads.empty:
            return self._empty_squads_dataframe()

        return self._normalize_squad_columns(squads)

    @staticmethod
    def _normalize_squad_columns(squads: pd.DataFrame) -> pd.DataFrame:
        """Normalize squad identifier columns."""
        result = squads.copy()

        for column in SQUAD_COLUMNS:
            result[column] = result[column].astype(str).str.strip()

        return result[SQUAD_COLUMNS]

    @staticmethod
    def _write_dataframe(dataframe: pd.DataFrame, output_path: Path) -> None:
        """Write a dataframe to CSV with project encoding."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(output_path, index=False, encoding=CSV_ENCODING)

    def _save_player_stats(self, player_stats: pd.DataFrame) -> None:
        """Save scraped player statistics to the weekly scrape folder."""
        self._write_dataframe(player_stats, self.player_stats_savepath)
        print(f"[INFO] player_stats saved to: {self.player_stats_savepath}")

    def _save_players(self, players: pd.DataFrame) -> None:
        """Save newly scraped players to the weekly scrape folder."""
        self._write_dataframe(players, self.players_savepath)
        print(f"[INFO] players saved to: {self.players_savepath}")

    def _save_squads(self, squads: pd.DataFrame) -> None:
        """Save missing squads to the weekly scrape folder."""
        self._write_dataframe(squads, self.squads_savepath)
        print(f"[INFO] squads saved to: {self.squads_savepath}")
        print(f"[INFO] Missing squads saved: {len(squads)}")

    def _get_unique_player_ids(self, player_stats: pd.DataFrame) -> list[str]:
        """Return unique player identifiers from player statistics."""
        if player_stats.empty or "player_id" not in player_stats.columns:
            return []

        return self._normalize_identifier_series(player_stats["player_id"]).unique().tolist()

    @staticmethod
    def _find_missing_player_ids(
        player_ids: list[str],
        db_player_ids: set[str],
    ) -> list[str]:
        """Return player identifiers that are not present in the database."""
        return [player_id for player_id in player_ids if player_id not in db_player_ids]

    def _scrape_missing_players(self, missing_player_ids: list[str]) -> pd.DataFrame:
        """Scrape missing player metadata by player identifier."""
        if not missing_player_ids:
            print("[CHECK] no missing players")
            return self._empty_players_dataframe()

        print("[CHECK] before scrape_players_by_ids")
        player_scraper = PlayersScraper(league_type=self.league_type)
        players = player_scraper.scrape_players_by_ids(missing_player_ids)
        print(f"[CHECK] scraped players rows: {len(players)}")
        return players

    @staticmethod
    def _get_new_player_ids(players: pd.DataFrame) -> set[str]:
        """Return player identifiers from newly scraped players."""
        if players.empty or "player_id" not in players.columns:
            return set()

        return set(players["player_id"].dropna().astype(str).str.strip().tolist())

    def _build_missing_squads(
        self,
        player_stats: pd.DataFrame,
        db_season: str,
        valid_player_ids: set[str],
    ) -> pd.DataFrame:
        """Build squad rows that are present in player statistics but missing in the database."""
        if player_stats.empty:
            return self._empty_squads_dataframe()

        squad_candidates = player_stats[["player_id", "club_id"]].dropna().copy()

        if squad_candidates.empty:
            return self._empty_squads_dataframe()

        squad_candidates["player_id"] = squad_candidates["player_id"].astype(str).str.strip()
        squad_candidates["club_id"] = squad_candidates["club_id"].astype(str).str.strip()
        squad_candidates["season"] = db_season
        squad_candidates = squad_candidates[
            squad_candidates["player_id"].isin(valid_player_ids)
        ][SQUAD_COLUMNS].drop_duplicates()

        existing_squads = self._get_existing_squads()

        missing_squads = squad_candidates.merge(
            existing_squads,
            on=SQUAD_COLUMNS,
            how="left",
            indicator=True,
        )
        missing_squads = missing_squads[missing_squads["_merge"] == "left_only"]

        return missing_squads[SQUAD_COLUMNS].reset_index(drop=True)

    def _write_empty_outputs(self) -> None:
        """Write empty live output files for a weekly run without data."""
        self._save_player_stats(self._empty_player_stats_dataframe())
        self._save_players(self._empty_players_dataframe())
        self._save_squads(self._empty_squads_dataframe())

    def _scrape_weekly_matches(self, season: int) -> pd.DataFrame:
        """Scrape and filter weekly matches for the current season."""
        matches_scraper = MatchesScraper(
            league=LEAGUES,
            start_year=season,
            end_year=season + 1,
            league_type=self.league_type,
        )
        matches_scraper.run()

        return self._filter_matches_csv(
            matches_path=Path(matches_scraper.matches_savepath),
            start_date=self._load_last_scrape_match_date(),
            end_date=date.today(),
        )

    def _scrape_weekly_player_stats(self) -> pd.DataFrame:
        """Scrape player statistics for the filtered weekly matches."""
        print("[CHECK] before player_stats_scraper.run()")
        player_stats_scraper = PlayerStatsScraper(league_type=self.league_type)
        player_stats = player_stats_scraper.run()
        print(f"[CHECK] player_stats rows: {len(player_stats)}")
        self._save_player_stats(player_stats)
        return player_stats

    def run(self) -> None:
        """Run the weekly live scraping process."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        season = get_saved_season()
        start_date = self._load_last_scrape_match_date()
        end_date = date.today()

        print("[INFO] Weekly live run started")

        if start_date > end_date:
            print("[INFO] Weekly window is empty")
            self._write_empty_outputs()
            print("[INFO] Weekly live run finished")
            return

        filtered_matches = self._scrape_weekly_matches(season)

        if filtered_matches.empty:
            print("[INFO] No finished matches in weekly window")
            self._write_empty_outputs()
            print("[INFO] Weekly live run finished")
            return

        player_stats = self._scrape_weekly_player_stats()

        if player_stats.empty:
            print("[WARN] No player_stats scraped for current weekly window")

        print("[CHECK] before unique_player_ids")
        unique_player_ids = self._get_unique_player_ids(player_stats)
        print(f"[CHECK] unique_player_ids: {len(unique_player_ids)}")

        print("[CHECK] before _get_db_player_ids")
        db_player_ids = self._get_db_player_ids()
        print(f"[CHECK] db_player_ids: {len(db_player_ids)}")

        missing_player_ids = self._find_missing_player_ids(unique_player_ids, db_player_ids)
        print(f"[CHECK] missing_player_ids: {len(missing_player_ids)}")

        players = self._scrape_missing_players(missing_player_ids)
        self._save_players(players)
        print("[CHECK] players saved")

        valid_player_ids = db_player_ids | self._get_new_player_ids(players)
        print(f"[CHECK] valid_player_ids: {len(valid_player_ids)}")

        db_season = self.season_to_db(season)
        print(f"[CHECK] before _build_missing_squads, db_season={db_season}")
        squads = self._build_missing_squads(
            player_stats=player_stats,
            db_season=db_season,
            valid_player_ids=valid_player_ids,
        )
        print(f"[CHECK] squads_df rows: {len(squads)}")

        self._save_squads(squads)
        print("[CHECK] squads saved")
        print("[INFO] Weekly live run finished")

    def close(self) -> None:
        """Dispose the database engine."""
        self.engine.dispose()


def run_weekly() -> None:
    """Run the weekly scraper and always close the database connection."""
    scraper = WeeklyAmateurScraper()

    try:
        scraper.run()
    finally:
        scraper.close()


def main() -> None:
    """Run the complete weekly live process from scraping to loading."""
    run_weekly()
    run_live_tl()


if __name__ == "__main__":
    main()
