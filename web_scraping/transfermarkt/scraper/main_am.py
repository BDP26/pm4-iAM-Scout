from web_scraping.transfermarkt.scraper.clubs import ClubsScraper
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper
from web_scraping.transfermarkt.scraper.players import PlayersScraper


PARAMS = {
    "league": ["1_liga_gr_2"],
    "start_year": 2020,
    "end_year": 2026,
    "league_type": "amateur",
}


def run_pro_scrape() -> None:
    print("Starting club scrape")
    clubs_scraper = ClubsScraper(
        league=PARAMS["league"],
        start_year=PARAMS["start_year"],
        end_year=PARAMS["end_year"],
        league_type=PARAMS["league_type"],
    )
    clubs_scraper.run()

    print("Starting player scrape")
    players_scraper = PlayersScraper(league_type=PARAMS["league_type"])
    players_scraper.run()

    print("Starting matches scrape")
    matches_scraper = MatchesScraper(
        league=PARAMS["league"],
        start_year=PARAMS["start_year"],
        end_year=PARAMS["end_year"],
        league_type=PARAMS["league_type"],
    )
    matches_scraper.run()
    
    print("Starting player stats scrape")
    player_stats_scraper = PlayerStatsScraper(league_type=PARAMS["league_type"])
    player_stats_scraper.run()


if __name__ == "__main__":
    run_pro_scrape()
