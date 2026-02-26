# web_scraping/club_scraping.py
import time
import pandas as pd
from pathlib import Path

from web_scraping.config import START_YEAR, END_YEAR, LEAGUE_URLS
from web_scraping.transfermarkt import make_session, fetch_html, parse_clubs

SLEEP_SECONDS = 1.5

def build_team_pool() -> tuple[pd.DataFrame, pd.DataFrame]:
    seasons = list(range(START_YEAR, END_YEAR))
    session = make_session()

    rows: list[dict] = []

    for league, url_tpl in LEAGUE_URLS.items():
        for season in seasons:
            url = url_tpl.format(season=season)
            html = fetch_html(session, url)

            for club in parse_clubs(html):
                rows.append({
                    "season": season,
                    "league": league,
                    "club_name": club["club_name"],
                    "club_id": club["club_id"],
                    "club_slug": club["club_slug"],
                })

            time.sleep(SLEEP_SECONDS)

    teams = pd.DataFrame(rows)

    teams_per_season = teams[["season", "league", "club_name"]].drop_duplicates().copy()

    teams_unique = (
        teams[["club_name", "club_id", "club_slug"]]
        .drop_duplicates(subset=["club_id"])
        .sort_values("club_name")
        .reset_index(drop=True)
    )

    return teams_per_season, teams_unique

def main() -> None:
    teams_per_season, teams_unique = build_team_pool()

    OUTPUT_DIR = Path(__file__).resolve().parent / "output"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    teams_per_season.to_csv(OUTPUT_DIR / "teams_per_season.csv", index=False, encoding="utf-8")
    teams_unique.to_csv(OUTPUT_DIR / "teams_unique.csv", index=False, encoding="utf-8")

if __name__ == "__main__":
    main()