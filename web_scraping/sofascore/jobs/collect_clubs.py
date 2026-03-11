from __future__ import annotations

import pandas as pd

from web_scraping.config import PRO_SEASONS
from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.clubs import parse_clubs_from_standings
from web_scraping.write_csv import write_pro_teams, write_pro_teams_per_season


def collect_pro_clubs() -> tuple[pd.DataFrame, pd.DataFrame]:
    client = SofaScoreClient()
    rows: list[dict] = []

    for season_id, season_label in PRO_SEASONS.items():
        payload = client.get_standings(season_id=season_id)

        for club in parse_clubs_from_standings(payload):
            rows.append(
                {
                    "season_id": season_id,
                    "season": season_label,
                    "league": "super_league",
                    "club_id": club["club_id"],
                    "club_name": club["club_name"],
                    "club_slug": club.get("club_slug"),
                }
            )

    clubs = pd.DataFrame(rows)

    if clubs.empty:
        raise ValueError("No pro clubs collected from SofaScore.")

    teams_per_season = (
        clubs[["club_id", "league", "season_id", "season"]]
        .drop_duplicates()
        .sort_values(["season_id", "club_id"])
        .reset_index(drop=True)
    )

    teams = (
        clubs[["club_id", "club_name", "club_slug"]]
        .drop_duplicates(subset=["club_id"])
        .sort_values("club_name")
        .reset_index(drop=True)
    )

    return teams_per_season, teams


def main() -> None:
    teams_per_season, teams = collect_pro_clubs()

    p1 = write_pro_teams_per_season(teams_per_season)
    p2 = write_pro_teams(teams)

    print(f"Saved: {p1}")
    print(f"Saved: {p2}")


if __name__ == "__main__":
    main()