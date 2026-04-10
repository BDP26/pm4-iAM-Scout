from pathlib import Path
import pandas as pd

from web_scraping.transfermarkt.client import HttpClient
from web_scraping.transfermarkt.parser.player_stats import PlayerStatsParser
from web_scraping.toolkit.logger import Logger


class PlayerStatsScraper:
    def __init__(self, league_type="amateur"):
        self.base_url = "https://www.transfermarkt.ch"
        self.match_url = "https://www.transfermarkt.ch/{matches_slug}/index/spielbericht/{match_id}"
        self.player_stat_url = (
            "https://www.transfermarkt.ch/{slug}/leistungsdatendetails/spieler/{player_id}/saison/{season}"
        )
        self.league_type = league_type

        self.project_root = Path(__file__).resolve().parents[3]
        self.data_dir = self.project_root / "data" / "scrape" / league_type
        self.matches_path = self.data_dir / "matches.csv"
        self.player_stats_savepath = self.data_dir / "player_stats.csv"

        self.client = HttpClient()
        self.parser = PlayerStatsParser()

        self.match_html_cache: dict[str, str] = {}
        self.goals_cache: dict[str, list[tuple[int, str]]] = {}
        self.player_season_cache: dict[tuple[int, str, str], list[dict]] = {}

    def _abs_url(self, href: str) -> str:
        href = (href or "").strip()
        if not href:
            return ""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if not href.startswith("/"):
            href = "/" + href
        return self.base_url + href

    def _clean_id(self, x) -> str:
        if x is None or pd.isna(x):
            return ""

        s = str(x).strip()
        if not s or s.lower() in {"nan", "<na>"}:
            return ""

        if s.endswith(".0"):
            s = s[:-2]

        return s

    def _minute_in_intervals(self, minute: int, intervals: list[tuple[int, int | None]]) -> bool:
        for start, end in intervals:
            off_excl = 10**9 if end is None else int(end)
            if int(start) <= int(minute) < off_excl:
                return True
        return False

    def load_inputs(self):
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
            str(r.match_id): {
                "season": int(r.season),
                "league": None if pd.isna(r.league) else str(r.league),
                "date": None if pd.isna(r.date) else str(r.date),
                "slug": str(r.matches_slug),
                "home": str(r.home_club_id),
                "away": str(r.away_club_id),
                "sh": None if pd.isna(r.home_goals) else int(r.home_goals),
                "sa": None if pd.isna(r.away_goals) else int(r.away_goals),
            }
            for r in self.matches.itertuples(index=False)
        }

        return self.matches

    def _get_match_html(self, match_id: str, matches_slug: str) -> str:
        if match_id not in self.match_html_cache:
            url = self.match_url.format(matches_slug=matches_slug, match_id=match_id)
            self.match_html_cache[match_id] = self.client.get(url)
        return self.match_html_cache[match_id]

    def _get_player_season_rows(self, season: int, player_id: str, player_slug: str) -> list[dict]:
        key = (int(season), str(player_id), str(player_slug))

        if key not in self.player_season_cache:
            url = self.player_stat_url.format(
                slug=player_slug,
                player_id=player_id,
                season=season,
            )
            html = self.client.get(url)
            self.player_season_cache[key] = self.parser.parse_player_leistungsdaten(html)

        return self.player_season_cache[key]

    def collect_player_stats(self):
        if not hasattr(self, "matches"):
            raise ValueError("Run load_inputs() first.")

        rows = []

        for m in self.matches.itertuples(index=False):
            match_id = self._clean_id(m.match_id)
            matches_slug = str(m.matches_slug).strip()

            if not match_id or not matches_slug:
                continue

            mi = self.match_info[match_id]
            season = int(mi["season"])
            home_id = mi["home"]
            away_id = mi["away"]

            try:
                mh = self._get_match_html(match_id, matches_slug)
            except Exception as e:
                print(f"[WARN] match report failed: match_id={match_id}, slug={matches_slug}, error={e}")
                continue

            try:
                player_refs = self.parser.parse_spielbericht_player_refs(mh)
            except Exception as e:
                print(f"[WARN] lineup parsing failed: match_id={match_id}, error={e}")
                continue

            if not player_refs:
                print(f"[WARN] no players found in match report: match_id={match_id}")
                continue

            if match_id not in self.goals_cache:
                try:
                    self.goals_cache[match_id] = self.parser.parse_spielbericht_goals(mh)
                except Exception as e:
                    print(f"[WARN] goal parsing failed: match_id={match_id}, error={e}")
                    self.goals_cache[match_id] = []

            goals = self.goals_cache[match_id]

            for p in player_refs:
                player_id = self._clean_id(p.get("player_id"))
                player_slug = str(p.get("player_slug") or "").strip()

                if not player_id or not player_slug:
                    continue

                try:
                    stats_rows = self._get_player_season_rows(season, player_id, player_slug)
                except Exception as e:
                    print(
                        f"[WARN] player stats failed: match_id={match_id}, "
                        f"player_id={player_id}, season={season}, error={e}"
                    )
                    continue

                stat_row = None
                for s in stats_rows:
                    stat_match_id = self._clean_id(s.get("match_id"))
                    if stat_match_id == match_id:
                        stat_row = s
                        break

                if stat_row is None:
                    continue

                club_id = self._clean_id(stat_row.get("club_id"))
                if not club_id:
                    continue

                if club_id != home_id and club_id != away_id:
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
                    sub_events = self.parser.parse_spielbericht_player_sub_events(mh, player_id)
                    start_eleven, on_min_eff, off_min_eff, intervals = (
                        self.parser.derive_start11_onoff_and_intervals(
                            minutes_played,
                            sub_events,
                        )
                    )
                except Exception as e:
                    print(f"[WARN] sub events failed: match_id={match_id}, player_id={player_id}, error={e}")
                    start_eleven, on_min_eff, off_min_eff, intervals = (
                        self.parser.derive_start11_onoff_and_intervals(
                            minutes_played,
                            [],
                        )
                    )

                on_min_out = None if start_eleven == 1 else int(on_min_eff)
                off_min_out = None if off_min_eff is None else int(off_min_eff)

                team_goals = sum(
                    1
                    for minute, cid in goals
                    if cid == club_id and self._minute_in_intervals(int(minute), intervals)
                )
                team_conceded = sum(
                    1
                    for minute, cid in goals
                    if cid != club_id and self._minute_in_intervals(int(minute), intervals)
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
                        "on_min": on_min_out,
                        "off_min": off_min_out,
                        "team_goals": int(team_goals),
                        "team_conceded": int(team_conceded),
                    }
                )

        cols = [
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

        self.player_stats = pd.DataFrame(rows)

        if self.player_stats.empty:
            self.player_stats = pd.DataFrame(columns=cols)
        else:
            self.player_stats = (
                self.player_stats
                .drop_duplicates(subset=["player_id", "match_id", "club_id"])
                .reset_index(drop=True)
            )

            for c in cols:
                if c not in self.player_stats.columns:
                    self.player_stats[c] = None

            self.player_stats = self.player_stats[cols]

        return self.player_stats

    def run(self):
        self.load_inputs()
        self.collect_player_stats()

        logger = Logger()
        logger.log(self.player_stats, "player_stats")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.player_stats.to_csv(self.player_stats_savepath, index=False, encoding="utf-8-sig")

        print(f"player_stats saved to: {self.player_stats_savepath}")

        return self.player_stats


def main(league_type):
    scraper = PlayerStatsScraper(
        league_type=league_type,
    )
    scraper.run()


if __name__ == "__main__":
    main("amateur")