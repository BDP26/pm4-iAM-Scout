"""
iAM-Scout API Server

This module provides a REST API interface for the iAM-Scout application, enabling access to
player data, team information, match statistics, and scouting insights.

Main endpoints:
- /teams: Get all available teams
- /players: Get all available players
- /players/{player_id}: Get specific player profile and statistics
- /top-players: Get highest-rated players for a team
- /match-search: Search for matches by ID or team combination
- /match-overview: Get match details and statistics
"""

from __future__ import annotations

import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Query
from pandas import DataFrame

import services

APP_TITLE = "iAM-Scout API"
ROOT_MESSAGE = "iAM-Scout API is running"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 80
DEFAULT_LEAGUE_TOP_PLAYER_LIMIT = 50
DEFAULT_RADIUS_KM = 25

app = FastAPI(title=APP_TITLE)


def dataframe_to_records(dataframe: DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to API response records."""
    return dataframe.to_dict(orient="records")


@app.get("/")
def root() -> dict[str, str]:
    """Return a simple API health message."""
    return {"message": ROOT_MESSAGE}


@app.get("/teams")
def api_get_teams() -> list[dict[str, Any]]:
    """Return all available teams."""
    return dataframe_to_records(services.get_teams())


@app.get("/players")
def api_get_players() -> list[dict[str, Any]]:
    """Return all available players."""
    return dataframe_to_records(services.get_players())


@app.get("/players/{player_id}")
def api_get_player(player_id: int) -> list[dict[str, Any]]:
    """Return profile information for one player."""
    return dataframe_to_records(services.get_player(player_id))


@app.get("/squads")
def api_get_squads(team_id: int, season: str) -> list[dict[str, Any]]:
    """Return the squad of a team for one season."""
    return dataframe_to_records(services.get_squads(team_id, season))


@app.get("/team-league")
def api_get_team_league(team_id: int, season: str) -> list[dict[str, Any]]:
    """Return league information for a team and season."""
    return dataframe_to_records(services.get_team_league(team_id, season))


@app.get("/top-players")
def api_get_top_players(team_id: int, season: str) -> list[dict[str, Any]]:
    """Return the highest rated players of a team in one season."""
    return dataframe_to_records(services.get_top_players(team_id, season))


@app.get("/player-stats/{player_id}")
def api_get_player_stats(player_id: int) -> list[dict[str, Any]]:
    """Return match statistics for one player."""
    return dataframe_to_records(services.get_player_stats(player_id))


@app.get("/games")
def api_get_games(team_id: int, season: str) -> list[dict[str, Any]]:
    """Return all games of a team in one season."""
    return dataframe_to_records(services.get_games(team_id, season))


@app.get("/match-search")
def api_get_match_search(
    match_id: int | None = None,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return matches by match ID or by two team IDs."""
    return dataframe_to_records(
        services.get_match_search(
            match_id=match_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
        )
    )


@app.get("/match-overview/{match_id}")
def api_get_match_overview(match_id: int) -> list[dict[str, Any]]:
    """Return overview information for one match."""
    return dataframe_to_records(services.get_match_overview(match_id))


@app.get("/match-player-stats/{match_id}")
def api_get_match_player_stats(match_id: int) -> list[dict[str, Any]]:
    """Return player statistics for one match."""
    return dataframe_to_records(services.get_match_player_stats(match_id))


@app.get("/leagues-seasons")
def api_get_leagues_seasons() -> list[dict[str, Any]]:
    """Return all league and season combinations."""
    return dataframe_to_records(services.get_leagues_seasons())


@app.get("/league-top-players")
def api_get_league_top_players(
    league: str,
    season: str,
    limit: int = DEFAULT_LEAGUE_TOP_PLAYER_LIMIT,
) -> list[dict[str, Any]]:
    """Return the highest rated players in a league and season."""
    return dataframe_to_records(
        services.get_league_top_players(league=league, season=season, limit=limit)
    )


@app.get("/clubs-in-radius")
def api_get_clubs_in_radius(
    zip_code: str,
    radius_km: int = DEFAULT_RADIUS_KM,
) -> list[dict[str, Any]]:
    """Return clubs within a given distance around a zip code."""
    return dataframe_to_records(
        services.get_clubs_in_radius(zip_code=zip_code, radius_km=radius_km)
    )


@app.get("/iam-scout")
def api_get_iam_scout_players(
    league: str | None = None,
    town: str | None = None,
    distance_enabled: bool = False,
    distance_km: int = DEFAULT_RADIUS_KM,
    age_min: int | None = None,
    age_max: int | None = None,
    positions: list[str] | None = Query(default=None),
    leagues: list[str] | None = Query(default=None),
) -> list[dict[str, Any]]:
    """Return filtered player recommendations for Smart Scout."""
    return dataframe_to_records(
        services.get_all_players_info(
            league=league,
            town=town,
            distance_enabled=distance_enabled,
            distance_km=distance_km,
            age_min=age_min,
            age_max=age_max,
            positions=positions,
            leagues=leagues,
        )
    )


def main() -> None:
    """Start the API server."""
    host = os.getenv("HOST", DEFAULT_HOST)
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))
    uvicorn.run("main:app", host=host, port=port)


if __name__ == "__main__":
    main()
