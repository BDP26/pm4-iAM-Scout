from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from web_scraping.transfermarkt.client import HttpClient
from web_scraping.transfermarkt.parser.player_stats import PlayerStatsParser
from web_scraping.transfermarkt.playwright_client import PlaywrightClient
from web_scraping.toolkit.logger import Logger


class PlayerStatsScraper:
    """Scraper for collecting detailed player statistics from individual match reports."""

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

    def __init__(self, league_type="amateur"):
        """Initialize player stats scraper with league type."""
        self.base_url = "https://www.transfermarkt.ch"
        self.match_url = "https://www.transfermarkt.ch/{matches_slug}/index/spielbericht/{match_id}"
        self.player_stat_url = (
            "https://www.transfermarkt.ch/{slug}/leistungsdatendetails/spieler/{player_id}/saison/{season}"
        )
        self.league_type = league_type

        self.matches_path = f"data/scrape/{league_type}/matches.csv"
        self.player_stats_savepath = f"data/scrape/{league_type}/player_stats.csv"

        self.client = HttpClient()

        self.browser_client = PlaywrightClient(
            browser_name="chromium",
            headless=True,
            max_attempts=4,
            nav_timeout_ms=30000,
            selector_timeout_ms=12000,
            networkidle_timeout_ms=5000,
        )

        self.parser = PlayerStatsParser()

        self.match_html_cache: dict[str, str] = {}
        self.goals_cache: dict[str, list[tuple[int, str]]] = {}
        self.player_season_cache: dict[tuple[int, str, str], list[dict]] = {}

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

    @staticmethod
    def _minute_in_intervals(
        minute: int,
        intervals: list[tuple[int, int | None]],
    ) -> bool:
        """Check if a minute falls within any of the given intervals."""
        for start, end in intervals:
            end_exclusive = 10**9 if end is None else int(end)
            if int(start) <= int(minute) < end_exclusive:
                return True
        return False

    def load_inputs(self):
        """Load match data from CSV file and prepare match information dictionary."""
        self.matches = pd.read_csv(
            self.matches_path,
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

        self.matches["match_id"] = self.matches["match_id"].apply(self._clean_id)
        self.matches["home_club_id"] = self.matches["home_club_id"].apply(self._clean_id)
        self.matches["away_club_id"] = self.matches["away_club_id"].apply(self._clean_id)
        self.matches["matches_slug"] = self.matches["matches_slug"].astype(str).str.strip()

        self.matches = self.matches[
            (self.matches["match_id"].astype(str).str.strip() != "")
            & (self.matches["matches_slug"].astype(str).str.strip() != "")
        ].copy()

        self.match_info = {
            str(row.match_id): {
                "season": int(row.season),
                "league": None if pd.isna(row.league) else str(row.league),
                "date": None if pd.isna(row.date) else str(row.date),
                "slug": str(row.matches_slug),
                "home": str(row.home_club_id),
                "away": str(row.away_club_id),
                "home_goals": None if pd.isna(row.home_goals) else int(row.home_goals),
                "away_goals": None if pd.isna(row.away_goals) else int(row.away_goals),
            }
            for row in self.matches.itertuples(index=False)
        }

        return self.matches

    def _get_match_html(self, match_id: str, matches_slug: str) -> str:
        """Fetch and cache match report HTML."""
        if match_id not in self.match_html_cache:
            url = self.match_url.format(matches_slug=matches_slug, match_id=match_id)
            self.match_html_cache[match_id] = self.client.get(url)
        return self.match_html_cache[match_id]

    def _get_player_season_rows(
        self,
        season: int,
        player_id: str,
        player_slug: str,
    ) -> list[dict]:
        """Fetch and cache player season statistics."""
        cache_key = (int(season), str(player_id), str(player_slug))

        if cache_key not in self.player_season_cache:
            url = self.player_stat_url.format(
                slug=player_slug,
                player_id=player_id,
                season=season,
            )

            parsed_rows: list[dict] = []

            for attempt in range(1, 3):
                html = self.browser_client.get(url, required_selector="table")
                parsed_rows = self.parser.parse_player_leistungsdaten(html)

                if parsed_rows:
                    break

                print(
                    f"[WARN] empty parsed player-stats rows {attempt}/2: "
                    f"player_id={player_id}, season={season}"
                )
                time.sleep(1.5 * attempt)

            self.player_season_cache[cache_key] = parsed_rows

        return self.player_season_cache[cache_key]

    def collect_player_stats(self):
        """Collect player statistics from match reports."""
        if not hasattr(self, "matches"):
            raise ValueError("Run load_inputs() first.")

        rows = []
        total_matches = len(self.matches)

        for match_index, match_row in enumerate(self.matches.itertuples(index=False), start=1):
            if match_index % 50 == 0:
                print(f"[INFO] Player stats progress: {match_index}/{total_matches} matches processed")

            match_id = self._clean_id(match_row.match_id)
            matches_slug = str(match_row.matches_slug).strip()

            if not match_id or not matches_slug:
                continue

            match_info = self.match_info[match_id]
            season = int(match_info["season"])
            home_club_id = match_info["home"]
            away_club_id = match_info["away"]

            try:
                match_html = self._get_match_html(match_id, matches_slug)
            except Exception as error:
                print(
                    f"[WARN] match report failed: "
                    f"match_id={match_id}, slug={matches_slug}"
                )
                continue

            try:
                player_refs = self.parser.parse_spielbericht_player_refs(match_html)
            except Exception as error:
                print(f"[WARN] lineup parsing failed: match_id={match_id}")
                continue

            if not player_refs:
                print(f"[WARN] no players found in match report: match_id={match_id}")
                continue

            if match_id not in self.goals_cache:
                try:
                    self.goals_cache[match_id] = self.parser.parse_spielbericht_goals(match_html)
                except Exception as error:
                    print(f"[WARN] goal parsing failed: match_id={match_id}")
                    self.goals_cache[match_id] = []

            goals = self.goals_cache[match_id]

            for player_ref in player_refs:
                player_id = self._clean_id(player_ref.get("player_id"))
                player_slug = str(player_ref.get("player_slug") or "").strip()

                if not player_id or not player_slug:
                    continue

                try:
                    stats_rows = self._get_player_season_rows(season, player_id, player_slug)
                except Exception as error:
                    print(
                        f"[WARN] player stats failed: "
                        f"match_id={match_id}, player_id={player_id}"
                    )
                    continue

                stat_row = None
                for stats_entry in stats_rows:
                    stat_match_id = self._clean_id(stats_entry.get("match_id"))
                    if stat_match_id == match_id:
                        stat_row = stats_entry
                        break

                if stat_row is None:
                    continue

                club_id = self._clean_id(stat_row.get("club_id"))
                if not club_id:
                    continue

                if club_id != home_club_id and club_id != away_club_id:
                    continue

                minutes_played = stat_row.get("minuten")
                if minutes_played is None or pd.isna(minutes_played):
                    continue

                try:
                    minutes_played = int(minutes_played)
                except (TypeError, ValueError):
                    continue

                if minutes_played <= 0:
                    continue

                try:
                    sub_events = self.parser.parse_spielbericht_player_sub_events(match_html, player_id)
                    start_eleven, on_minute_eff, off_minute_eff, intervals = (
                        self.parser.derive_start11_onoff_and_intervals(
                            minutes_played,
                            sub_events,
                        )
                    )
                except Exception as error:
                    print(
                        f"[WARN] sub events failed: "
                        f"match_id={match_id}, player_id={player_id}"
                    )
                    start_eleven, on_minute_eff, off_minute_eff, intervals = (
                        self.parser.derive_start11_onoff_and_intervals(
                            minutes_played,
                            [],
                        )
                    )

                on_minute_output = None if start_eleven == 1 else int(on_minute_eff)
                off_minute_output = None if off_minute_eff is None else int(off_minute_eff)

                team_goals = sum(
                    1
                    for minute, club_id_goal in goals
                    if club_id_goal == club_id and self._minute_in_intervals(int(minute), intervals)
                )
                team_conceded = sum(
                    1
                    for minute, club_id_goal in goals
                    if club_id_goal != club_id and self._minute_in_intervals(int(minute), intervals)
                )

                rows.append(
                    {
                        "player_id": player_id,
                        "match_id": match_id,
                        "club_id": club_id,
                        "goals": int(stat_row.get("tore") or 0),
                        "assists": int(stat_row.get("assists") or 0),
                        "yellow": int(stat_row.get("gelb") or 0),
                        "yellow_red": int(stat_row.get("gelb_rot") or 0),
                        "red": int(stat_row.get("rot") or 0),
                        "start_eleven": int(start_eleven),
                        "minutes": minutes_played,
                        "on_min": on_minute_output,
                        "off_min": off_minute_output,
                        "team_goals": int(team_goals),
                        "team_conceded": int(team_conceded),
                    }
                )

        self.player_stats = pd.DataFrame(rows)

        if self.player_stats.empty:
            self.player_stats = pd.DataFrame(columns=self.PLAYER_STATS_COLUMNS)
        else:
            self.player_stats = (
                self.player_stats
                .drop_duplicates(subset=["player_id", "match_id", "club_id"])
                .reset_index(drop=True)
            )

            for column in self.PLAYER_STATS_COLUMNS:
                if column not in self.player_stats.columns:
                    self.player_stats[column] = None

            self.player_stats = self.player_stats[self.PLAYER_STATS_COLUMNS]

        return self.player_stats

    def close(self) -> None:
        """Close browser resources."""
        self.browser_client.close()

    def run(self):
        """Execute complete player stats scraping workflow."""
        try:
            self.load_inputs()
            self.collect_player_stats()

            try:
                logger = Logger()
                logger.log(self.player_stats, "player_stats")
            except Exception as error:
                print(f"[WARN] logger failed for player_stats: {error}")

            Path(self.player_stats_savepath).parent.mkdir(parents=True, exist_ok=True)
            self.player_stats.to_csv(
                self.player_stats_savepath,
                index=False,
                encoding="utf-8-sig",
            )

            print(f"player_stats saved to: {self.player_stats_savepath}")
            return self.player_stats
        finally:
            self.close()


def main(league_type):
    """Execute player stats scraper with given league type."""
    scraper = PlayerStatsScraper(league_type=league_type)
    scraper.run()


if __name__ == "__main__":
    main("pro")