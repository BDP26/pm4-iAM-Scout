from web_scraping.sofascore.scraper.players import SofaScorePlayersScraper
from web_scraping.sofascore.scraper.ratings import SofaScorePlayerStatsScraper

SEASONS = ["25/26", "24/25", "23/24", "22/23", "21/22", "20/21"]
PLAYERS_PATH = "data/scrape/pro/players_sofascore.csv"
RATINGS_PATH = "data/scrape/pro/ratings.csv"
MIN_DATE = "2024-07-01"
COMPETITION = "Swiss Super League"
CLIENT_RESET_EVERY = 20
SAVE_EVERY_PLAYERS = 20


def run_sofascore_scrape() -> None:
    """Execute complete SofaScore scraping workflow."""
    print("[INFO] Step 1/2: Scraping SofaScore players")
    players_scraper = SofaScorePlayersScraper(seasons=SEASONS)
    players_scraper.players_savepath = PLAYERS_PATH
    players_scraper.run()

    print("[INFO] Step 2/2: Scraping SofaScore player ratings")
    ratings_scraper = SofaScorePlayerStatsScraper(
        players_path=PLAYERS_PATH,
        savepath=RATINGS_PATH,
        competition=COMPETITION,
        min_date=MIN_DATE,
        client_reset_every=CLIENT_RESET_EVERY,
        save_every_players=SAVE_EVERY_PLAYERS,
    )
    ratings_scraper.run()

    print("[INFO] SofaScore scraping completed successfully")


if __name__ == "__main__":
    run_sofascore_scrape()
