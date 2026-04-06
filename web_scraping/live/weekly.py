# web_scraping/live/weekly.py

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from web_scraping.live.yearly import LEAGUES, get_current_season
from web_scraping.transfermarkt.scraper.matches import MatchesScraper
from web_scraping.transfermarkt.scraper.player_stats import PlayerStatsScraper

LAST_SCRAPES_PATH = "../runtime/last_scrapes.json"

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

    df.to_csv(matches_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] Filtered matches saved to: {matches_path}")
    print(f"[INFO] Matches kept between {start_date} and {end_date}: {len(df)}")


def run_weekly() -> None:
    season = get_current_season()
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
    player_stats_scraper.run()

    # missing_player_id = []

    # for loop
    # If player_id not in players
    # missing_player_id.append(player_id)
    # for loop

    # scraper = PlayersScraper(league_type="amateur")
    # df_players = scraper.scrape_players_by_ids(player_ids)

    # If player in squad not in squads
    #   append or create squad

    ### Transform ###

    ### In DB einlesen ###

    ### CSV löschen ###



    print("[INFO] Weekly live run finished")