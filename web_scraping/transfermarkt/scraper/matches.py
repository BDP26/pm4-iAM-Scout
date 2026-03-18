import pandas as pd

from web_scraping.transfermarkt.parser.matches import MatchesParser
from web_scraping.transfermarkt.client import HttpClient
from web_scraping.toolkit.logger import Logger


class MatchesScraper:
    def __init__(self, league, start_year=2020, end_year=2026, league_type="amateur"):
        self.matches_url = {
            "sl": "https://www.transfermarkt.ch/super-league/gesamtspielplan/wettbewerb/C1?saison_id={season}",
            "pl": "https://www.transfermarkt.ch/promotion-league/gesamtspielplan/wettbewerb/CHPR?saison_id={season}",
            "1_liga_gr_1": "https://www.transfermarkt.ch/1-liga-gruppe-1/gesamtspielplan/wettbewerb/CHC1?saison_id={season}",
            "1_liga_gr_2": "https://www.transfermarkt.ch/1-liga-gruppe-2/gesamtspielplan/wettbewerb/CHC2?saison_id={season}",
            "1_liga_gr_3": "https://www.transfermarkt.ch/1-liga-gruppe-3/gesamtspielplan/wettbewerb/CHC3?saison_id={season}",
        }

        self.league = league if isinstance(league, list) else [league]
        self.seasons = list(range(start_year, end_year))
        self.league_type = league_type

        self.matches_savepath = f"data/scrape/{league_type}/matches.csv"

        self.client = HttpClient()
        self.parser = MatchesParser()

    def collect_matches(self):
        rows = []

        for s in self.seasons:
            for l in self.league:
                url = self.matches_url[l].format(season=s)
                html = self.client.get(url)

                for match in self.parser.parse_matches(html):
                    if not match.get("match_id"):
                        continue

                    rows.append(
                        {
                            "match_id": match["match_id"],
                            "season": s,
                            "league": l,
                            "date": match.get("datum"),
                            "home_club_id": match.get("home_club_id"),
                            "away_club_id": match.get("away_club_id"),
                            "home_goals": match.get("score_home"),
                            "away_goals": match.get("score_away"),
                            "matches_slug": match.get("matches_slug"),
                        }
                    )

        if not rows:
            raise ValueError("No matches collected. Check URLs, season formatting, or parser output.")

        ordered_columns = [
            "match_id",
            "season",
            "league",
            "date",
            "home_club_id",
            "away_club_id",
            "home_goals",
            "away_goals",
            "matches_slug",
        ]

        df = pd.DataFrame(rows)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        today = pd.Timestamp.today().normalize()

        df = df[
            (df["date"] < today) &
            (df["home_goals"].notna()) &
            (df["away_goals"].notna())
            ]

        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        self.matches = (
            df.drop_duplicates(subset=["match_id"])
            .sort_values(["season", "league", "date", "match_id"])
            .reset_index(drop=True)
            .reindex(columns=ordered_columns)
        )

        return self.matches

    def run(self):
        self.collect_matches()

        logger = Logger()
        logger.log(self.matches, "matches")

        self.matches.to_csv(self.matches_savepath, index=False, encoding="utf-8-sig")

        print(f"matches saved to: {self.matches_savepath}")

        return self.matches


def main(league, start_year, end_year, league_type):
    scraper = MatchesScraper(
        league=league,
        start_year=start_year,
        end_year=end_year,
        league_type=league_type,
    )
    scraper.run()


if __name__ == "__main__":
    main(["pl"], 2025, 2026, "amateur")