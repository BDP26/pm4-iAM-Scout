from pathlib import Path
import pandas as pd

from web_scraping.transfermarkt.client import HttpClient
from web_scraping.transfermarkt.parser.player_stats import PlayerStatsParser
from web_scraping.toolkit.logger import Logger


class PlayerStatsScraper:
    def __init__(self, start_year=2020, end_year=2026, league_type="amateur"):
        self.base_url = "https://www.transfermarkt.ch"
        self.player_stat_url = "https://www.transfermarkt.ch/{slug}/leistungsdatendetails/spieler/{player_id}/saison/{season}"

        self.seasons = list(range(start_year, end_year))

        self.players_path = f"data/scrape/{league_type}/players.csv"
        self.matches_path = f"data/scrape/{league_type}/matches.csv"

        self.player_stats_savepath = f"data/scrape/{league_type}/player_stats.csv"

        self.client = HttpClient()
        self.parser = PlayerStatsParser()

        self.match_html_cache: dict[str, str] = {}
        self.goals_cache: dict[str, list[tuple[int, str]]] = {}

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
        self.players = pd.read_csv(
            self.players_path,
            dtype={"player_id": "string", "player_slug": "string"},
        )

        self.matches = pd.read_csv(
            self.matches_path,
            dtype={
                "match_id": "string",
                "home_club_id": "string",
                "away_club_id": "string",
                "home_goals": "Int64",
                "away_goals": "Int64",
            },
        )

        self.players["player_id"] = self.players["player_id"].apply(self._clean_id)
        self.players["player_slug"] = self.players["player_slug"].astype(str).str.strip()

        self.matches["match_id"] = self.matches["match_id"].apply(self._clean_id)
        self.matches["home_club_id"] = self.matches["home_club_id"].apply(self._clean_id)
        self.matches["away_club_id"] = self.matches["away_club_id"].apply(self._clean_id)

        self.players = self.players.dropna(subset=["player_id", "player_slug"]).copy()
        self.players = self.players[
            (self.players["player_id"].astype(str).str.strip() != "")
            & (self.players["player_slug"].astype(str).str.strip() != "")
        ].copy()

        self.match_info = {
            str(r.match_id): {
                "home": str(r.home_club_id),
                "away": str(r.away_club_id),
                "sh": None if pd.isna(r.home_goals) else int(r.home_goals),
                "sa": None if pd.isna(r.away_goals) else int(r.away_goals),
            }
            for r in self.matches.itertuples(index=False)
        }
        self.match_ids_set = set(self.match_info.keys())

        return self.players, self.matches

    def collect_player_stats(self):
        if not hasattr(self, "players") or not hasattr(self, "matches"):
            raise ValueError("Run load_inputs() first.")

        rows = []

        for season in self.seasons:
            for p in self.players.itertuples(index=False):
                player_id = self._clean_id(p.player_id)
                slug = str(p.player_slug).strip()

                if not player_id or not slug:
                    continue

                url = self.player_stat_url.format(
                    slug=slug,
                    player_id=player_id,
                    season=season,
                )

                try:
                    html = self.client.get(url)
                    stats_rows = self.parser.parse_player_leistungsdaten(html)
                except Exception as e:
                    print(f"[WARN] player stats failed: player_id={player_id}, season={season}, url={url}, error={e}")
                    continue

                for s in stats_rows:
                    match_id = self._clean_id(s.get("match_id"))
                    if not match_id or match_id not in self.match_ids_set:
                        continue

                    club_id = self._clean_id(s.get("club_id"))
                    if not club_id:
                        continue

                    mi = self.match_info[match_id]
                    home_id, away_id = mi["home"], mi["away"]

                    if club_id != home_id and club_id != away_id:
                        continue

                    minutes_played = s.get("minuten")
                    if minutes_played is None or int(minutes_played) <= 0:
                        continue

                    if match_id not in self.match_html_cache:
                        href = s.get("match_href") or ""
                        match_url = self._abs_url(href)
                        if not match_url:
                            continue

                        try:
                            self.match_html_cache[match_id] = self.client.get(match_url)
                        except Exception as e:
                            print(f"[WARN] match report failed: match_id={match_id}, url={match_url}, error={e}")
                            continue

                    mh = self.match_html_cache[match_id]

                    if match_id not in self.goals_cache:
                        try:
                            self.goals_cache[match_id] = self.parser.parse_spielbericht_goals(mh)
                        except Exception as e:
                            print(f"[WARN] goal parsing failed: match_id={match_id}, error={e}")
                            self.goals_cache[match_id] = []

                    goals = self.goals_cache[match_id]

                    try:
                        sub_events = self.parser.parse_spielbericht_player_sub_events(mh, player_id)
                        start_eleven, on_min_eff, off_min_eff, intervals = (
                            self.parser.derive_start11_onoff_and_intervals(
                                int(minutes_played),
                                sub_events,
                            )
                        )
                    except Exception as e:
                        print(f"[WARN] sub events failed: match_id={match_id}, player_id={player_id}, error={e}")
                        continue

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
                            "goals": int(s.get("tore") or 0),
                            "assists": int(s.get("assists") or 0),
                            "yellow": int(s.get("gelb") or 0),
                            "yellow_red": int(s.get("gelb_rot") or 0),
                            "red": int(s.get("rot") or 0),
                            "start_eleven": int(start_eleven),
                            "minutes": int(minutes_played),
                            "on_min": on_min_out,
                            "off_min": off_min_out,
                            "team_goals": int(team_goals),
                            "team_conceded": int(team_conceded),
                        }
                    )

        self.player_stats = (
            pd.DataFrame(rows)
            .drop_duplicates(subset=["player_id", "match_id"])
            .reset_index(drop=True)
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

        if self.player_stats.empty:
            self.player_stats = pd.DataFrame(columns=cols)
        else:
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

        Path(self.player_stats_savepath).parent.mkdir(parents=True, exist_ok=True)
        self.player_stats.to_csv(self.player_stats_savepath, index=False, encoding="utf-8-sig")

        print(f"player_stats saved to: {self.player_stats_savepath}")

        return self.player_stats


def main():
    scraper = PlayerStatsScraper(
        start_year=2024,
        end_year=2026,
        league_type="pro",
    )
    scraper.run()


if __name__ == "__main__":
    main()