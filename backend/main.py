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


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "80"))
    uvicorn.run("main:app", host=host, port=port)