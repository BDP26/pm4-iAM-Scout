from typing import Any

import pandas as pd
import requests

API_URL = "http://160.85.253.241:80"
REQUEST_TIMEOUT_SECONDS = 30


def _get_dataframe(path: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Fetch data from the API and return it as a dataframe."""
    try:
        response = requests.get(
            f"{API_URL}{path}",
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"API request failed for path '{path}'.") from error

    return pd.DataFrame(response.json())


def get_teams() -> pd.DataFrame:
    """Return all available teams."""
    return _get_dataframe("/teams")


def get_players() -> pd.DataFrame:
    """Return all available players."""
    return _get_dataframe("/players")


def get_player(player_id: int) -> pd.DataFrame:
    """Return one player by player id."""
    return _get_dataframe(f"/players/{player_id}")


def get_squads(team_id: int, season: str) -> pd.DataFrame:
    """Return the squad of a team for a season."""
    return _get_dataframe(
        "/squads",
        params={"team_id": team_id, "season": season},
    )


def get_team_league(team_id: int, season: str) -> pd.DataFrame:
    """Return the league of a team for a season."""
    return _get_dataframe(
        "/team-league",
        params={"team_id": team_id, "season": season},
    )


def get_top_players(team_id: int, season: str) -> pd.DataFrame:
    """Return the top players of a team for a season."""
    return _get_dataframe(
        "/top-players",
        params={"team_id": team_id, "season": season},
    )


def get_player_stats(player_id: int) -> pd.DataFrame:
    """Return all available statistics for one player."""
    return _get_dataframe(f"/player-stats/{player_id}")


def get_games(team_id: int, season: str) -> pd.DataFrame:
    """Return all games of a team for a season."""
    return _get_dataframe(
        "/games",
        params={"team_id": team_id, "season": season},
    )


def get_match_search(
    match_id: int | None = None,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
) -> pd.DataFrame:
    """Return matches filtered by match id or participating teams."""
    params = {
        key: value
        for key, value in {
            "match_id": match_id,
            "team_a_id": team_a_id,
            "team_b_id": team_b_id,
        }.items()
        if value is not None
    }

    return _get_dataframe("/match-search", params=params)


def get_match_overview(match_id: int) -> pd.DataFrame:
    """Return the overview data for one match."""
    return _get_dataframe(f"/match-overview/{match_id}")


def get_match_player_stats(match_id: int) -> pd.DataFrame:
    """Return player statistics for one match."""
    return _get_dataframe(f"/match-player-stats/{match_id}")


def get_leagues_seasons() -> pd.DataFrame:
    """Return available league and season combinations."""
    return _get_dataframe("/leagues-seasons")


def get_league_top_players(
    league: str,
    season: str,
    limit: int = 50,
) -> pd.DataFrame:
    """Return the top players of a league for a season."""
    return _get_dataframe(
        "/league-top-players",
        params={"league": league, "season": season, "limit": limit},
    )


def get_clubs_in_radius(zip_code: str, radius_km: int = 25) -> pd.DataFrame:
    """Return clubs within a radius around a zip code."""
    return _get_dataframe(
        "/clubs-in-radius",
        params={"zip_code": zip_code, "radius_km": radius_km},
    )


def get_iam_scout(params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return Smart Scout results for the provided filter parameters."""
    return _get_dataframe("/iam-scout", params=params)
