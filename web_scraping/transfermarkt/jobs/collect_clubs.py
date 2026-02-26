import time
import pandas as pd

from web_scraping.config import START_YEAR, END_YEAR, LEAGUE_URLS
from web_scraping.output.write_csv import write_teams_per_season, write_teams_unique
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.clubs import parse_clubs

SLEEP_SECONDS = 1.5


def collect_clubs() -> tuple[pd.DataFrame, pd.DataFrame]:
    seasons = list(range(START_YEAR, END_YEAR))
    session = make_session()

    rows: list[dict] = []

    for league, url_tpl in LEAGUE_URLS.items():
        for season in seasons:
            url = url_tpl.format(season=season)
            html = fetch_html(session, url)

            for club in parse_clubs(html):
                if not club.get("club_id") or not club.get("club_slug"):
                    continue

                rows.append(
                    {
                        "season": season,
                        "league": league,
                        "club_name": club["club_name"],
                        "club_id": club["club_id"],
                        "club_slug": club["club_slug"],
                    }
                )

            time.sleep(SLEEP_SECONDS)

    teams = pd.DataFrame(rows)

    teams_per_season = teams[["season", "league", "club_id"]].drop_duplicates().copy()

    teams_unique = (
        teams[["club_name", "club_id", "club_slug"]]
        .drop_duplicates(subset=["club_id"])
        .sort_values("club_name")
        .reset_index(drop=True)
    )

    return teams_per_season, teams_unique


def main() -> None:
    teams_per_season, teams_unique = collect_clubs()

    p1 = write_teams_per_season(teams_per_season)
    p2 = write_teams_unique(teams_unique)

    print(f"Saved: {p1}")
    print(f"Saved: {p2}")


if __name__ == "__main__":
    main()