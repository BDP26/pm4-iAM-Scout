from __future__ import annotations

def parse_clubs_from_standings(payload: dict) -> list[dict]:
    standings = payload.get("standings", [])
    if not standings:
        raise ValueError("No standings found in SofaScore payload.")

    rows = standings[0].get("rows", [])
    clubs: list[dict] = []

    for row in rows:
        team = row.get("team", {})
        team_id = team.get("id")
        team_name = team.get("name")
        team_slug = team.get("slug")

        if not team_id or not team_name:
            continue

        clubs.append(
            {
                "club_id": str(team_id),
                "club_name": team_name,
                "club_slug": team_slug,
            }
        )

    return clubs