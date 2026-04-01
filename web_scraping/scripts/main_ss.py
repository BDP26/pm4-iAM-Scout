from web_scraping.sofascore.scraper.players import SofaScorePlayersScraper
from web_scraping.sofascore.scraper.ratings import SofaScorePlayerStatsScraper


def main() -> None:
    seasons = ["25/26", "24/25", "23/24", "22/23", "21/22", "20/21"]
    players_path = "data/scrape/pro/players_sofascore.csv"
    ratings_path = "data/scrape/pro/ratings.csv"
    min_date = "2024-07-01"
    competition = "Swiss Super League"

    print("[INFO] Step 1/2: Scrape SofaScore players")
    players_scraper = SofaScorePlayersScraper(seasons=seasons)
    players_scraper.players_savepath = players_path
    players_scraper.run()

    print("[INFO] Step 2/2: Scrape SofaScore ratings")
    ratings_scraper = SofaScorePlayerStatsScraper(
        players_path=players_path,
        savepath=ratings_path,
        competition=competition,
        min_date=min_date,
        client_reset_every=20,
        save_every_players=20,
    )
    ratings_scraper.run()

    print("[INFO] SofaScore scrape finished")


if __name__ == "__main__":
    main()