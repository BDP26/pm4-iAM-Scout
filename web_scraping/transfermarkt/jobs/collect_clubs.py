import time
import pandas as pd

from web_scraping.config import (
    START_YEAR,
    END_YEAR,
    LEAGUE_URLS,
    SLEEP_SECONDS,
    LOCATION_URL,
    STADIUM_URL,
)
from web_scraping.write_csv import write_teams_per_season, write_teams
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.clubs import parse_clubs
from web_scraping.transfermarkt.parser.locations import (
    parse_plz_location,
    parse_plz_location_stadium,
)


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

    clubs = pd.DataFrame(rows)

    teams_per_season = clubs[["club_id", "league", "season"]].drop_duplicates().copy()

    teams = (
        clubs[["club_name", "club_id", "club_slug"]]
        .drop_duplicates(subset=["club_id"])
        .sort_values("club_name")
        .reset_index(drop=True)
    )

    plz_list: list[str | None] = []
    location_list: list[str | None] = []

    for row in teams.itertuples(index=False):
        club_id = str(row.club_id).strip()
        slug = str(row.club_slug).strip()

        plz: str | None = None
        location: str | None = None

        url_facts = LOCATION_URL.format(slug=slug, club_id=club_id)
        try:
            html = fetch_html(session, url_facts)
            plz, location = parse_plz_location(html)
        except Exception as e:
            print(f"[WARN] facts failed for club_id={club_id}, slug={slug}: {e}")

        if not (plz and location):
            url_stadium = STADIUM_URL.format(slug=slug, club_id=club_id)
            try:
                html = fetch_html(session, url_stadium)
                plz, location = parse_plz_location_stadium(html)
            except Exception as e:
                print(f"[WARN] stadium failed for club_id={club_id}, slug={slug}: {e}")

        plz_list.append(plz)
        location_list.append(location)

        time.sleep(SLEEP_SECONDS)

    teams["PLZ"] = plz_list
    teams["location"] = location_list
    teams = teams[["club_id", "club_name", "PLZ", "location", "club_slug"]]

    return teams_per_season, teams


def main() -> None:
    teams_per_season, teams = collect_clubs()

    p1 = write_teams_per_season(teams_per_season)
    p2 = write_teams(teams)

    print(f"Saved: {p1}")
    print(f"Saved: {p2}")


if __name__ == "__main__":
    main()