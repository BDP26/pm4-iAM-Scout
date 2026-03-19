from web_scraping.transfermarkt.scraper.clubs import ClubsScraper
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper
from web_scraping.transfermarkt.scraper.players import PlayersScraper


PARAMS = {
    "league": ["pl"],
    "start_year": 2020,
    "end_year": 2026,
    "league_type": "amateur",
}


def run_pro_scrape() -> None:
    """
    clubs_scraper = ClubsScraper(
        league=PARAMS["league"],
        start_year=PARAMS["start_year"],
        end_year=PARAMS["end_year"],
        league_type=PARAMS["league_type"],
    )
    clubs_scraper.run()

    players_scraper = PlayersScraper(league_type=PARAMS["league_type"])
    players_scraper.run()

    matches_scraper = MatchesScraper(
        league=PARAMS["league"],
        start_year=PARAMS["start_year"],
        end_year=PARAMS["end_year"],
        league_type=PARAMS["league_type"],
    )
    matches_scraper.run()
    """
    print("Starting with player stats scraping")
    player_stats_scraper = PlayerStatsScraper(league_type=PARAMS["league_type"])
    player_stats_scraper.run()


if __name__ == "__main__":
    run_pro_scrape()
