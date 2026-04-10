import os
import pandas as pd
import requests

API_URL = "http://160.85.253.241:80"
#API_URL = os.getenv("API_URL", "http://localhost:80")


def _get_df(path, params=None):
    response = requests.get(f"{API_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return pd.DataFrame(response.json())


def get_teams():
    return _get_df("/teams")


def get_players():
    return _get_df("/players")


def get_player(player_id: int):
    return _get_df(f"/players/{player_id}")


def get_squads(team_id: int, season: str):
    return _get_df("/squads", params={"team_id": team_id, "season": season})


def get_team_league(team_id: int, season: str):
    return _get_df("/team-league", params={"team_id": team_id, "season": season})


def get_top_players(team_id: int, season: str):
    return _get_df("/top-players", params={"team_id": team_id, "season": season})


def get_player_stats(player_id: int):
    return _get_df(f"/player-stats/{player_id}")
