from fastapi import FastAPI
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


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "80"))
    uvicorn.run("main:app", host=host, port=port)
