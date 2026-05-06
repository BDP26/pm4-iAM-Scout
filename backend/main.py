from fastapi import FastAPI, Query
import services

app = FastAPI()

@app.get("/")
def root():
    return {"message": "iAM-Scout API läuft 🚀"}

@app.get("/teams")
def api_get_teams():
    df = services.get_teams()
    return df.to_dict(orient="records")

@app.get("/players")
def api_get_players():
    df = services.get_players()
    return df.to_dict(orient="records")

@app.get("/players/{player_id}")
def api_get_player(player_id: int):
    df = services.get_player(player_id)
    return df.to_dict(orient="records")

@app.get("/squads")
def api_get_squads(team_id: int, season: str):
    df = services.get_squads(team_id, season)
    return df.to_dict(orient="records")

@app.get("/team-league")
def api_get_team_league(team_id: int, season: str):
    df = services.get_team_league(team_id, season)
    return df.to_dict(orient="records")

@app.get("/top-players")
def api_get_top_players(team_id: int, season: str):
    df = services.get_top_players(team_id, season)
    return df.to_dict(orient="records")

@app.get("/player-stats/{player_id}")
def api_get_player_stats(player_id: int):
    df = services.get_player_stats(player_id)
    return df.to_dict(orient="records")

@app.get("/games")
def api_get_games(team_id: int, season: str):
    df = services.get_games(team_id, season)
    return df.to_dict(orient="records")

@app.get("/match-search")
def api_get_match_search(
    match_id: int | None = None,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
):
    df = services.get_match_search(
        match_id=match_id,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
    )
    return df.to_dict(orient="records")

@app.get("/match-overview/{match_id}")
def api_get_match_overview(match_id: int):
    df = services.get_match_overview(match_id)
    return df.to_dict(orient="records")

@app.get("/match-player-stats/{match_id}")
def api_get_match_player_stats(match_id: int):
    df = services.get_match_player_stats(match_id)
    return df.to_dict(orient="records")


@app.get("/leagues-seasons")
def api_get_leagues_seasons():
    df = services.get_leagues_seasons()
    return df.to_dict(orient="records")


@app.get("/league-top-players")
def api_get_league_top_players(league: str, season: str, limit: int = 50):
    df = services.get_league_top_players(league=league, season=season, limit=limit)
    return df.to_dict(orient="records")


@app.get("/clubs-in-radius")
def api_get_clubs_in_radius(zip_code: str, radius_km: int = 25):
    df = services.get_clubs_in_radius(zip_code=zip_code, radius_km=radius_km)
    return df.to_dict(orient="records")


@app.get("/iam-scout")
def api_iam_scout(
    league: str | None = None,
    town: str | None = None,
    distance_enabled: bool = False,
    distance_km: int = 25,
    age_min: int | None = None,
    age_max: int | None = None,
    positions: list[str] | None = Query(None),
    leagues: list[str] | None = Query(None),
):
    df = services.get_all_players_info(
        league=league,
        town=town,
        distance_enabled=distance_enabled,
        distance_km=distance_km,
        age_min=age_min,
        age_max=age_max,
        positions=positions,
        leagues=leagues,
    )
    return df.to_dict(orient="records")


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "80"))
    uvicorn.run("main:app", host=host, port=port)
