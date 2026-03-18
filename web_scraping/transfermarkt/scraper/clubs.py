import pandas as pd

from web_scraping.transfermarkt.parser.clubs import ClubsParser
from web_scraping.transfermarkt.client import HttpClient
from web_scraping.toolkit.logger import Logger


class ClubsScraper:
    def __init__(self, league, start_year=2020, end_year=2026, league_type="amateur"):
        self.league_url = {
            "sl": "https://www.transfermarkt.ch/super-league/startseite/wettbewerb/C1/plus/?saison_id={season}",
            "pl": "https://www.transfermarkt.ch/promotion-league/tabelle/wettbewerb/CHPR?saison_id={season}",
            "1_liga_gr_1": "https://www.transfermarkt.ch/1-liga-gruppe-1/tabelle/wettbewerb/CHC1?saison_id={season}",
            "1_liga_gr_2": "https://www.transfermarkt.ch/1-liga-gruppe-2/tabelle/wettbewerb/CHC2?saison_id={season}",
            "1_liga_gr_3": "https://www.transfermarkt.ch/1-liga-gruppe-3/tabelle/wettbewerb/CHC3?saison_id={season}",
        }

        self.location_url = "https://www.transfermarkt.ch/{slug}/datenfakten/verein/{club_id}"
        self.stadium_url = "https://www.transfermarkt.ch/{slug}/stadion/verein/{club_id}"

        self.league = league if isinstance(league, list) else [league]
        self.seasons = list(range(start_year, end_year))

        self.clubs_savepath = f"data/scrape/{league_type}/clubs.csv"
        self.cps_savepath = f"data/scrape/{league_type}/clubs_per_season.csv"

        self.client = HttpClient()
        self.parser = ClubsParser()

    def collect_clubs(self):
        rows = []

        for s in self.seasons:
            for l in self.league:
                url = self.league_url[l].format(season=s)
                html = self.client.get(url)

                for club in self.parser.parse_clubs(html):
                    if not club.get("club_id") or not club.get("club_slug"):
                        continue

                    rows.append(
                        {
                            "season": s,
                            "league": l,
                            "club_name": club["club_name"],
                            "club_id": club["club_id"],
                            "club_slug": club["club_slug"],
                        }
                    )

        if not rows:
            raise ValueError("No clubs collected. Check URLs, season formatting, or parser output.")

        clubs_df = pd.DataFrame(rows)

        self.clubs_per_season = (
            clubs_df[["club_id", "league", "season"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )

        self.clubs = (
            clubs_df[["club_name", "club_id", "club_slug"]]
            .drop_duplicates(subset=["club_id"])
            .sort_values("club_name")
            .reset_index(drop=True)
        )

        return self.clubs, self.clubs_per_season

    def collect_locations(self):
        if not hasattr(self, "clubs") or self.clubs.empty:
            raise ValueError("Run collect_clubs() first.")

        plz_list = []
        location_list = []

        for row in self.clubs.itertuples(index=False):
            club_id = str(row.club_id).strip()
            slug = str(row.club_slug).strip()

            plz = None
            location = None

            url_location = self.location_url.format(slug=slug, club_id=club_id)
            try:
                html = self.client.get(url_location)
                plz, location = self.parser.parse_plz_location(html)
            except Exception as e:
                print(f"[WARN] facts failed for club_id={club_id}, slug={slug}: {e}")

            if not (plz and location):
                url_stadium = self.stadium_url.format(slug=slug, club_id=club_id)
                try:
                    html = self.client.get(url_stadium)
                    plz, location = self.parser.parse_plz_location_stadium(html)
                except Exception as e:
                    print(f"[WARN] stadium failed for club_id={club_id}, slug={slug}: {e}")

            plz_list.append(plz)
            location_list.append(location)

        self.clubs["PLZ"] = plz_list
        self.clubs["location"] = location_list
        self.clubs = self.clubs[["club_id", "club_name", "PLZ", "location", "club_slug"]]

        return self.clubs

    def run(self):
        self.collect_clubs()
        self.collect_locations()
        
        logger = Logger()
        logger.log(self.clubs, "clubs")
        logger.log(self.clubs_per_season, "clubs_per_season")

        self.clubs.to_csv(self.clubs_savepath, index=False, encoding="utf-8-sig")
        self.clubs_per_season.to_csv(self.cps_savepath, index=False, encoding="utf-8-sig")
        


        print(f"clubs saved to: {self.clubs_savepath}")
        print(f"clubs_per_season saved to: {self.cps_savepath}")


def main():
    scraper = ClubsScraper(
<<<<<<< HEAD
        league=["sl"],
        start_year=2024,
        end_year=2026,
        league_type="pro",
=======
        league=["pl"],
        start_year=2025,
        end_year=2026,
        league_type="amateur",
>>>>>>> 983be76 (scrape parameter)
    )
    scraper.run()


if __name__ == "__main__":
    main()