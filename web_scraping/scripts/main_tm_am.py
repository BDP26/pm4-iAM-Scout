from web_scraping.transfermarkt.scraper.clubs import ClubsScraper
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper
from web_scraping.transfermarkt.scraper.players import PlayersScraper

SCRAPER_PARAMS = {
    "league": ["1_liga_gr_3"],
    "start_year": 2025,
    "end_year": 2026,
    "league_type": "amateur",
}


def run_amateur_scrape() -> None:
    """Execute complete Transfermarkt scraping workflow for amateur league."""
    print("[INFO] Step 1/4: Scraping clubs")
    clubs_scraper = ClubsScraper(
        league=SCRAPER_PARAMS["league"],
        start_year=SCRAPER_PARAMS["start_year"],
        end_year=SCRAPER_PARAMS["end_year"],
        league_type=SCRAPER_PARAMS["league_type"],
    )
    clubs_scraper.run()

    print("[INFO] Step 2/4: Scraping players and squads")
    players_scraper = PlayersScraper(league_type=SCRAPER_PARAMS["league_type"])
    players_scraper.run()

    print("[INFO] Step 3/4: Scraping matches")
    matches_scraper = MatchesScraper(
        league=SCRAPER_PARAMS["league"],
        start_year=SCRAPER_PARAMS["start_year"],
        end_year=SCRAPER_PARAMS["end_year"],
        league_type=SCRAPER_PARAMS["league_type"],
    )
    matches_scraper.run()

    print("[INFO] Step 4/4: Scraping player statistics")
    player_stats_scraper = PlayerStatsScraper(league_type=SCRAPER_PARAMS["league_type"])
    player_stats_scraper.run()

    print("[INFO] Amateur league scraping completed successfully")


if __name__ == "__main__":
    run_amateur_scrape()
