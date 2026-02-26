import time
from pathlib import Path
import pandas as pd

from web_scraping.config import LOCATION_URL, STADIUM_URL
from web_scraping.output.write_csv import write_teams_unique_with_locations
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.locations import (
    parse_plz_location,
    parse_plz_location_stadium,
)

SLEEP_SECONDS = 1.5


def get_locations(teams_unique: pd.DataFrame) -> pd.DataFrame:
    required = {"club_id", "club_slug"}
    missing = required - set(teams_unique.columns)
    if missing:
        raise ValueError(f"teams_unique is missing columns: {missing}")

    session = make_session()
    df = teams_unique.copy()

    plz_list: list[str | None] = []
    location_list: list[str | None] = []

    for row in df.itertuples(index=False):
        club_id = str(getattr(row, "club_id")).strip()
        slug = str(getattr(row, "club_slug")).strip()

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

    df["PLZ"] = plz_list
    df["location"] = location_list
    return df


def main() -> None:
    out_dir = Path(__file__).resolve().parents[2] / "output"
    teams_unique_path = out_dir / "teams_unique.csv"

    teams_unique = pd.read_csv(teams_unique_path)
    teams_unique_with_locations = get_locations(teams_unique)

    saved_path = write_teams_unique_with_locations(teams_unique_with_locations, output_dir=out_dir)
    print(f"Saved: {saved_path}")


if __name__ == "__main__":
    main()