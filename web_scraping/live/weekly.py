from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from web_scraping.live.yearly import LEAGUES, get_saved_season
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper
from web_scraping.transfermarkt.scraper.players import PlayersScraper


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "scrape" / "amateur"
LAST_SCRAPES_PATH = PROJECT_ROOT / "web_scraping" / "runtime" / "last_scrapes.json"

MATCHES_SAVEPATH = DATA_DIR / "matches.csv"
PLAYER_STATS_SAVEPATH = DATA_DIR / "player_stats.csv"
PLAYERS_SAVEPATH = DATA_DIR / "players.csv"
SQUADS_SAVEPATH = DATA_DIR / "squads.csv"


def _load_last_scrape_match_date() -> date:
    if not LAST_SCRAPES_PATH.exists():
        raise FileNotFoundError(f"last_scrapes.json not found: {LAST_SCRAPES_PATH}")

    with LAST_SCRAPES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    last_scrape_match = data.get("matches")
    if not last_scrape_match:
        raise KeyError("Key 'matches' not found in last_scrapes.json")

    return datetime.strptime(last_scrape_match, "%d.%m.%y %H:%M:%S").date()


def _filter_matches_csv(matches_path: Path, start_date: date, end_date: date) -> None:
    if not matches_path.exists():
        raise FileNotFoundError(f"matches.csv not found: {matches_path}")

    df = pd.read_csv(
        matches_path,
        dtype={
            "match_id": "string",
            "season": "Int64",
            "league": "string",
            "date": "string",
            "home_club_id": "string",
            "away_club_id": "string",
            "home_goals": "Int64",
            "away_goals": "Int64",
            "matches_slug": "string",
        },
    )

    if df.empty:
        print("[INFO] matches.csv is empty, nothing to filter")
        return

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    df = df[
        df["date"].notna()
        & (df["date"] >= start_date)
        & (df["date"] <= end_date)
    ].copy()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    matches_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(matches_path, index=False, encoding="utf-8-sig")

    print(f"[INFO] Filtered matches saved to: {matches_path}")
    print(f"[INFO] Matches kept between {start_date} and {end_date}: {len(df)}")


def season_to_db(current_season: int) -> str:
    current_season = int(current_season)
    return f"{str(current_season)[-2:]}/{str(current_season + 1)[-2:]}"


def run_weekly() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    season = get_saved_season()
    date_today = date.today()
    last_scrape_match_date = _load_last_scrape_match_date()

    print("[INFO] Weekly live run started")

    matches_scraper = MatchesScraper(
        league=LEAGUES,
        start_year=season,
        end_year=season + 1,
        league_type="amateur",
    )
    matches_scraper.run()

    matches_path = Path(matches_scraper.matches_savepath)
    _filter_matches_csv(
        matches_path=matches_path,
        start_date=last_scrape_match_date,
        end_date=date_today,
    )

    player_stats_scraper = PlayerStatsScraper(league_type="amateur")
    player_stats = player_stats_scraper.run()

    PLAYER_STATS_SAVEPATH.parent.mkdir(parents=True, exist_ok=True)
    player_stats.to_csv(PLAYER_STATS_SAVEPATH, index=False, encoding="utf-8-sig")
    print(f"player_stats saved to: {PLAYER_STATS_SAVEPATH}")

    engine = create_engine(
        "postgresql+psycopg2://postgres:postgres@localhost:5434/iamscout"
    )

    unique_player_ids = (
        player_stats["player_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    with engine.connect() as conn:
        result = conn.execute(text("SELECT player_id FROM players"))
        db_player_ids = {str(row[0]) for row in result}

    missing_player_id = []

    for player_id in unique_player_ids:
        if player_id not in db_player_ids:
            missing_player_id.append(player_id)

    player_scraper = PlayersScraper(league_type="amateur")
    players = player_scraper.scrape_players_by_ids(missing_player_id)

    PLAYERS_SAVEPATH.parent.mkdir(parents=True, exist_ok=True)
    players.to_csv(PLAYERS_SAVEPATH, index=False, encoding="utf-8-sig")
    print(f"players saved to: {PLAYERS_SAVEPATH}")

    db_season = season_to_db(season)

    squad_candidates = (
        player_stats[["player_id", "club_id"]]
        .dropna()
        .copy()
    )

    missing_squads = []

    if not squad_candidates.empty:
        squad_candidates["player_id"] = squad_candidates["player_id"].astype(str).str.strip()
        squad_candidates["club_id"] = squad_candidates["club_id"].astype(str).str.strip()
        squad_candidates["season"] = db_season
        squad_candidates = squad_candidates[["player_id", "club_id", "season"]].drop_duplicates()

        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT player_id, club_id, season
                FROM squads
            """))
            existing_squads = {(str(row[0]), str(row[1]), str(row[2])) for row in result}

            for _, row in squad_candidates.iterrows():
                squad_key = (row["player_id"], row["club_id"], row["season"])

                if squad_key not in existing_squads:
                    missing_squads.append(squad_key)

                    conn.execute(
                        text("""
                            INSERT INTO squads (player_id, club_id, season)
                            VALUES (:player_id, :club_id, :season)
                        """),
                        {
                            "player_id": row["player_id"],
                            "club_id": row["club_id"],
                            "season": row["season"],
                        }
                    )

    squads_df = pd.DataFrame(missing_squads, columns=["player_id", "club_id", "season"])
    SQUADS_SAVEPATH.parent.mkdir(parents=True, exist_ok=True)
    squads_df.to_csv(SQUADS_SAVEPATH, index=False, encoding="utf-8-sig")
    print(f"squads saved to: {SQUADS_SAVEPATH}")
    print(f"[INFO] Missing squads inserted: {len(missing_squads)}")

    ### Transform ###

    ### In DB einlesen ###

    ### CSV löschen ###

    print("[INFO] Weekly live run finished")


if __name__ == "__main__":
    run_weekly()