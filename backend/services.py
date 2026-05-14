"""
iAM-Scout Backend Services

This module provides core business logic for accessing and manipulating scouting data,
including player search, team analysis, match statistics, and geolocation-based scouting.
It handles database connections, data retrieval, filtering, and transformations.

Main services:
- Player and team search and filtering
- Smart scout location-based recommendations
- Match and league analytics
- Player rating and statistics aggregation
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.elements import TextClause

load_dotenv()

DEFAULT_DATABASE_PORT = "5432"
DEFAULT_RADIUS_KM = 25
MINIMUM_LEAGUE_GAMES = 10
EARTH_RADIUS_KM = 6371.0
POSTCODES_PATH = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "post-codes.csv"
SMART_SCOUT_COLUMNS = [
    "player_name",
    "position",
    "club_name",
    "club_location",
    "age",
    "rating",
]
LEAGUE_CODE_MAP = {
    "1. Liga": ["1_liga_gr_1", "1_liga_gr_2", "1_liga_gr_3"],
    "1. Liga Gruppe 1": ["1_liga_gr_1"],
    "1. Liga Gruppe 2": ["1_liga_gr_2"],
    "1. Liga Gruppe 3": ["1_liga_gr_3"],
    "Promotion League": ["pl"],
    "pl": ["pl"],
    "1_liga_gr_1": ["1_liga_gr_1"],
    "1_liga_gr_2": ["1_liga_gr_2"],
    "1_liga_gr_3": ["1_liga_gr_3"],
}
NORMALIZED_LEAGUE_CODE_MAP = {}


def normalize_text(value: Any) -> str:
    """Normalize text for robust filter comparisons."""
    cleaned_characters = [
        character
        for character in str(value or "").lower()
        if character.isalnum() or character == "_" or character.isspace()
    ]
    return " ".join("".join(cleaned_characters).split())


NORMALIZED_LEAGUE_CODE_MAP = {
    normalize_text(league_name): league_codes
    for league_name, league_codes in LEAGUE_CODE_MAP.items()
}


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the database engine."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)

    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    port = os.getenv("DB_PORT", DEFAULT_DATABASE_PORT)

    missing_variables = [
        variable_name
        for variable_name, variable_value in {
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_HOST": host,
            "DB_NAME": database,
        }.items()
        if not variable_value
    ]

    if missing_variables:
        raise RuntimeError(
            f"Missing database configuration values: {', '.join(missing_variables)}"
        )

    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    )


def get_connection():
    """Return a database connection."""
    return get_engine().connect()


def run_query(query: str | TextClause, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a SQL query and return the result as a dataframe."""
    statement = text(query) if isinstance(query, str) else query
    with get_engine().connect() as connection:
        return pd.read_sql_query(statement, connection, params=params or {})


@lru_cache(maxsize=1)
def load_postcodes_dataframe() -> pd.DataFrame:
    """Load and clean Swiss postcode coordinates."""
    postcodes_df = pd.read_csv(POSTCODES_PATH, dtype={"zip": str})
    postcodes_df = postcodes_df[["zip", "town", "lat", "lng"]].dropna()
    postcodes_df["zip"] = postcodes_df["zip"].astype(str).str.strip()
    postcodes_df["town"] = postcodes_df["town"].astype(str).str.strip()
    postcodes_df["lat"] = pd.to_numeric(postcodes_df["lat"], errors="coerce")
    postcodes_df["lng"] = pd.to_numeric(postcodes_df["lng"], errors="coerce")
    return postcodes_df.dropna().drop_duplicates(subset=["zip"], keep="first")


def normalize_league_codes(values: list[str] | None) -> list[str]:
    """Convert user-facing league names to stored league codes."""
    normalized_codes = []

    for value in values or []:
        if value is None:
            continue

        league_code = normalize_text(value)
        mapped_codes = NORMALIZED_LEAGUE_CODE_MAP.get(league_code, [value])
        normalized_codes.extend(mapped_codes)

    return sorted(set(normalized_codes))


def normalize_positions(positions: list[str] | str | None) -> list[str]:
    """Normalize position filter values."""
    if isinstance(positions, str):
        positions = [positions]

    return [
        " ".join(str(position).split()).lower()
        for position in positions or []
        if position
    ]


def calculate_haversine_distance_km(
    start_latitude: float,
    start_longitude: float,
    end_latitude: pd.Series,
    end_longitude: pd.Series,
) -> pd.Series:
    """Calculate vectorized haversine distances in kilometers."""
    start_latitude_rad = np.radians(start_latitude)
    end_latitude_rad = np.radians(end_latitude.astype(float))
    latitude_delta = np.radians(end_latitude.astype(float) - start_latitude)
    longitude_delta = np.radians(end_longitude.astype(float) - start_longitude)

    haversine_value = (
        np.sin(latitude_delta / 2) ** 2
        + np.cos(start_latitude_rad)
        * np.cos(end_latitude_rad)
        * np.sin(longitude_delta / 2) ** 2
    )
    central_angle = 2 * np.arctan2(
        np.sqrt(haversine_value),
        np.sqrt(1 - haversine_value),
    )
    return EARTH_RADIUS_KM * central_angle


def get_center_coordinates(zip_code: str) -> tuple[float, float] | None:
    """Return latitude and longitude for a zip code."""
    postcodes_df = load_postcodes_dataframe()
    center_rows = postcodes_df[postcodes_df["zip"] == str(zip_code).strip()]

    if center_rows.empty:
        return None

    center_row = center_rows.iloc[0]
    return float(center_row["lat"]), float(center_row["lng"])


def get_zip_code_for_town(town: str) -> str | None:
    """Return the first matching zip code for a town."""
    postcodes_df = load_postcodes_dataframe()
    town_rows = postcodes_df[postcodes_df["town"] == str(town).strip()]

    if town_rows.empty:
        return None

    return str(town_rows.iloc[0]["zip"]).strip()


def get_clubs_with_coordinates() -> pd.DataFrame:
    """Return clubs enriched with postcode coordinates."""
    clubs_df = run_query(
        """
        SELECT club_id, club_name, plz, location
        FROM clubs
        WHERE plz IS NOT NULL
        """
    )
    postcodes_df = load_postcodes_dataframe()[["zip", "lat", "lng"]]
    clubs_df["zip"] = clubs_df["plz"].astype(str).str.strip()
    clubs_df = clubs_df.merge(postcodes_df, on="zip", how="left")
    return clubs_df.dropna(subset=["lat", "lng"])


def get_club_ids_for_location_filter(
    town: str | None = None,
    distance_enabled: bool = False,
    distance_km: int = DEFAULT_RADIUS_KM,
) -> list[int] | None:
    """Return club IDs matching the optional location filter."""
    if not distance_enabled or not town:
        return None

    town_zip_code = get_zip_code_for_town(town)
    if town_zip_code is None:
        return []

    center_coordinates = get_center_coordinates(town_zip_code)
    if center_coordinates is None:
        return []

    center_latitude, center_longitude = center_coordinates
    clubs_df = get_clubs_with_coordinates()
    clubs_df["distance_km"] = calculate_haversine_distance_km(
        center_latitude,
        center_longitude,
        clubs_df["lat"],
        clubs_df["lng"],
    )
    return clubs_df.loc[
        clubs_df["distance_km"] <= float(distance_km),
        "club_id",
    ].astype(int).tolist()


def get_teams() -> pd.DataFrame:
    """Return all teams ordered by name."""
    return run_query("SELECT club_id, club_name FROM clubs ORDER BY club_name")


def get_players() -> pd.DataFrame:
    """Return all players ordered by name."""
    return run_query("SELECT player_id, player_name FROM players ORDER BY player_name")


def get_player(player_id: int) -> pd.DataFrame:
    """Return profile data for one player."""
    return run_query(
        """
        SELECT player_name, nationality, date_of_birth, height, position
        FROM players
        WHERE player_id = :player_id
        """,
        {"player_id": player_id},
    )


def get_squads(team_id: int, season: str) -> pd.DataFrame:
    """Return the squad of a team for one season."""
    return run_query(
        """
        SELECT
            p.player_name,
            p.position
        FROM squads s
        JOIN players p
            ON s.player_id = p.player_id
        WHERE s.club_id = :team_id
            AND s.season = :season
        ORDER BY p.position
        """,
        {"team_id": team_id, "season": season},
    )


def get_team_league(team_id: int, season: str) -> pd.DataFrame:
    """Return league metadata for a team and season."""
    return run_query(
        """
        SELECT *
        FROM clubs_per_season
        WHERE club_id = :team_id
            AND season = :season
        """,
        {"team_id": team_id, "season": season},
    )


def get_top_players(team_id: int, season: str) -> pd.DataFrame:
    """Return the highest rated players of a team in one season."""
    return run_query(
        """
        SELECT *
        FROM (
            SELECT
                p.player_name,
                COUNT(ps.match_id) AS games,
                ROUND(AVG(ps.rating)::numeric, 1) AS avg_rating
            FROM player_stats ps
            JOIN matches m
                ON ps.match_id = m.match_id
            JOIN players p
                ON ps.player_id = p.player_id
            WHERE m.season = :season
                AND ps.club_id = :team_id
                AND ps.rating IS NOT NULL
            GROUP BY p.player_name
        ) ranked_players
        ORDER BY avg_rating DESC
        """,
        {"team_id": team_id, "season": season},
    )


def get_player_stats(player_id: int) -> pd.DataFrame:
    """Return match statistics for one player."""
    return run_query(
        """
        SELECT
            m.game_date,
            m.season,
            m.league,
            c.club_name AS club_name,
            opp.club_name AS opponent_name,
            CASE
                WHEN ps.club_id = m.home_club_id THEN 'home'
                ELSE 'away'
            END AS home_away,
            CASE
                WHEN ps.club_id = m.home_club_id THEN m.home_goals
                ELSE m.away_goals
            END AS goals_for,
            CASE
                WHEN ps.club_id = m.home_club_id THEN m.away_goals
                ELSE m.home_goals
            END AS goals_against,
            CASE
                WHEN (
                    (ps.club_id = m.home_club_id AND m.home_goals > m.away_goals)
                    OR (ps.club_id = m.away_club_id AND m.away_goals > m.home_goals)
                ) THEN 'Win'
                WHEN m.home_goals = m.away_goals THEN 'Draw'
                ELSE 'Loss'
            END AS result,
            ps.goals,
            ps.assists,
            ps.yellow,
            ps.yellow_red,
            ps.red,
            ps.start_eleven,
            ps.minutes,
            ps.on_min,
            ps.off_min,
            ps.rating
        FROM player_stats ps
        JOIN matches m
            ON ps.match_id = m.match_id
        JOIN clubs c
            ON ps.club_id = c.club_id
        JOIN clubs opp
            ON opp.club_id = CASE
                WHEN ps.club_id = m.home_club_id THEN m.away_club_id
                ELSE m.home_club_id
            END
        WHERE ps.player_id = :player_id
        ORDER BY m.game_date DESC
        """,
        {"player_id": player_id},
    )


def get_games(team_id: int, season: str) -> pd.DataFrame:
    """Return all games of a team in one season."""
    return run_query(
        """
        SELECT
            m.match_id,
            m.game_date,
            m.season,
            m.league,
            home.club_name AS home_team,
            away.club_name AS away_team,
            m.home_goals,
            m.away_goals,
            CASE
                WHEN m.home_club_id = :team_id THEN 'home'
                ELSE 'away'
            END AS home_away,
            CASE
                WHEN m.home_club_id = :team_id THEN away.club_name
                ELSE home.club_name
            END AS opponent
        FROM matches m
        JOIN clubs home
            ON m.home_club_id = home.club_id
        JOIN clubs away
            ON m.away_club_id = away.club_id
        WHERE m.season = :season
            AND (m.home_club_id = :team_id OR m.away_club_id = :team_id)
        ORDER BY m.game_date DESC
        """,
        {"team_id": team_id, "season": season},
    )


def build_match_search_filter(
    match_id: int | None = None,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """Build the SQL filter for match search."""
    if match_id is not None:
        return "m.match_id = :match_id", {"match_id": match_id}

    if team_a_id is None or team_b_id is None:
        return None, {}

    return (
        "((m.home_club_id = :team_a_id AND m.away_club_id = :team_b_id) "
        "OR (m.home_club_id = :team_b_id AND m.away_club_id = :team_a_id))",
        {"team_a_id": team_a_id, "team_b_id": team_b_id},
    )


def get_match_search(
    match_id: int | None = None,
    team_a_id: int | None = None,
    team_b_id: int | None = None,
) -> pd.DataFrame:
    """Return matches by match ID or by two team IDs."""
    where_sql, params = build_match_search_filter(match_id, team_a_id, team_b_id)

    if where_sql is None:
        return pd.DataFrame()

    return run_query(
        f"""
        SELECT
            m.match_id,
            m.game_date,
            m.season,
            m.league,
            home.club_name AS home_team,
            away.club_name AS away_team,
            m.home_goals,
            m.away_goals
        FROM matches m
        JOIN clubs home
            ON m.home_club_id = home.club_id
        JOIN clubs away
            ON m.away_club_id = away.club_id
        WHERE {where_sql}
        ORDER BY m.game_date DESC
        """,
        params,
    )


def get_match_overview(match_id: int) -> pd.DataFrame:
    """Return overview data for one match."""
    return run_query(
        """
        SELECT
            m.match_id,
            m.game_date,
            m.season,
            m.league,
            m.home_club_id,
            home.club_name AS home_team,
            m.home_goals,
            m.away_club_id,
            away.club_name AS away_team,
            m.away_goals
        FROM matches m
        JOIN clubs home
            ON m.home_club_id = home.club_id
        JOIN clubs away
            ON m.away_club_id = away.club_id
        WHERE m.match_id = :match_id
        """,
        {"match_id": match_id},
    )


def get_match_player_stats(match_id: int) -> pd.DataFrame:
    """Return player statistics for one match."""
    return run_query(
        """
        SELECT
            ps.match_id,
            ps.club_id,
            c.club_name,
            p.player_name,
            p.position,
            ps.goals,
            ps.assists,
            ps.yellow,
            ps.yellow_red,
            ps.red,
            ps.start_eleven,
            ps.minutes,
            ps.on_min,
            ps.off_min,
            ps.rating
        FROM player_stats ps
        JOIN players p
            ON ps.player_id = p.player_id
        JOIN clubs c
            ON ps.club_id = c.club_id
        WHERE ps.match_id = :match_id
        ORDER BY c.club_name, p.player_name
        """,
        {"match_id": match_id},
    )


def get_leagues_seasons() -> pd.DataFrame:
    """Return all league and season combinations."""
    return run_query(
        """
        SELECT DISTINCT league, season
        FROM matches
        WHERE league IS NOT NULL
            AND season IS NOT NULL
        ORDER BY league, season DESC
        """
    )


def get_league_top_players(
    league: str,
    season: str,
    limit: int = 50,
) -> pd.DataFrame:
    """Return the highest rated players in a league and season."""
    return run_query(
        """
        SELECT
            p.player_name,
            c.club_name,
            COUNT(ps.match_id) AS games,
            ROUND(AVG(ps.rating)::numeric, 2) AS avg_rating
        FROM player_stats ps
        JOIN matches m
            ON ps.match_id = m.match_id
        JOIN players p
            ON ps.player_id = p.player_id
        JOIN clubs c
            ON ps.club_id = c.club_id
        WHERE m.league = :league
            AND m.season = :season
            AND ps.rating IS NOT NULL
        GROUP BY p.player_name, c.club_name
        HAVING COUNT(ps.match_id) >= :minimum_games
        ORDER BY avg_rating DESC, games DESC
        LIMIT :limit
        """,
        {
            "league": league,
            "season": season,
            "minimum_games": MINIMUM_LEAGUE_GAMES,
            "limit": int(limit),
        },
    )


def get_clubs_in_radius(
    zip_code: str,
    radius_km: int = DEFAULT_RADIUS_KM,
) -> pd.DataFrame:
    """Return clubs within a radius around a zip code."""
    center_coordinates = get_center_coordinates(zip_code)

    if center_coordinates is None:
        return pd.DataFrame()

    center_latitude, center_longitude = center_coordinates
    clubs_df = get_clubs_with_coordinates()
    clubs_df["distance_km"] = calculate_haversine_distance_km(
        center_latitude,
        center_longitude,
        clubs_df["lat"],
        clubs_df["lng"],
    )
    result_df = clubs_df[clubs_df["distance_km"] <= float(radius_km)].copy()
    result_df = result_df.sort_values(["distance_km", "club_name"])
    result_df["distance_km"] = result_df["distance_km"].round(1)
    return result_df[["club_id", "club_name", "plz", "location", "distance_km"]]


def build_smart_scout_filters(
    league: str | None = None,
    leagues: list[str] | None = None,
    positions: list[str] | str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    club_ids: list[int] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Build filters and parameters for the Smart Scout query."""
    where_clauses = ["p.prediction IS NOT NULL"]
    params: dict[str, Any] = {}

    selected_league_codes = normalize_league_codes([league] if league else [])
    selected_league_codes.extend(normalize_league_codes(leagues or []))
    selected_league_codes = sorted(set(selected_league_codes))
    position_values = normalize_positions(positions)

    if age_min is not None and age_max is not None:
        where_clauses.append(
            "p.date_of_birth BETWEEN "
            "(CURRENT_DATE - make_interval(years => :age_max)) "
            "AND (CURRENT_DATE - make_interval(years => :age_min))"
        )
        params["age_min"] = int(age_min)
        params["age_max"] = int(age_max)

    if position_values:
        where_clauses.append(
            "regexp_replace(lower(coalesce(p.position, '')), '\\s+', ' ', 'g') "
            "= ANY(:position_values)"
        )
        params["position_values"] = position_values

    if club_ids is not None:
        where_clauses.append("lc.club_id = ANY(:club_ids)")
        params["club_ids"] = [int(club_id) for club_id in club_ids]

    if selected_league_codes:
        where_clauses.append("lc.league = ANY(:league_codes)")
        params["league_codes"] = selected_league_codes

    return where_clauses, params


def get_all_players_info(
    league: str | None = None,
    town: str | None = None,
    distance_enabled: bool = False,
    distance_km: int = DEFAULT_RADIUS_KM,
    age_min: int | None = None,
    age_max: int | None = None,
    positions: list[str] | str | None = None,
    leagues: list[str] | None = None,
) -> pd.DataFrame:
    """Return filtered player recommendations for Smart Scout."""
    club_ids = get_club_ids_for_location_filter(
        town=town,
        distance_enabled=bool(distance_enabled),
        distance_km=distance_km,
    )

    if club_ids == []:
        return pd.DataFrame(columns=SMART_SCOUT_COLUMNS)

    where_clauses, params = build_smart_scout_filters(
        league=league,
        leagues=leagues,
        positions=positions,
        age_min=age_min,
        age_max=age_max,
        club_ids=club_ids,
    )

    return run_query(
        f"""
        WITH latest_club AS (
            SELECT DISTINCT ON (s.player_id)
                s.player_id,
                s.club_id,
                c.club_name,
                c.location AS club_location,
                cps.league,
                s.season
            FROM squads s
            JOIN clubs c
                ON c.club_id = s.club_id
            JOIN clubs_per_season cps
                ON cps.club_id = s.club_id
                AND cps.season = s.season
            ORDER BY
                s.player_id,
                split_part(s.season, '/', 1)::int DESC,
                split_part(s.season, '/', 2)::int DESC,
                s.club_id DESC
        )
        SELECT
            p.player_name,
            p.position,
            lc.club_name,
            lc.club_location,
            EXTRACT(YEAR FROM age(CURRENT_DATE, p.date_of_birth))::int AS age,
            p.prediction AS rating
        FROM players p
        INNER JOIN latest_club lc
            ON lc.player_id = p.player_id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY rating DESC, p.player_name
        """,
        params,
    )
