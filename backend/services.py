import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os
from math import radians, sin, cos, sqrt, atan2

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def run_query(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_teams():
    query = "SELECT club_id, club_name FROM clubs ORDER BY club_name"
    return run_query(query)

def get_players():
    query = "SELECT player_id, player_name FROM players ORDER BY player_name"
    return run_query(query)

def get_player(player_id):
    query = f"""
        SELECT player_name, nationality, date_of_birth, height, position
        FROM players
        WHERE player_id = {player_id}
    """
    return run_query(query)


def get_squads(team_id, season):
    query = f"""
        SELECT 
            p.player_name,
            p.position
        FROM squads s
        JOIN players p 
            ON s.player_id = p.player_id
        WHERE s.club_id = {team_id}
        AND s.season = '{season}'
        ORDER BY p.position
    """
    return run_query(query)

def get_team_league(team_id, season):
    query = f"""
        SELECT *
        FROM clubs_per_season
        WHERE club_id = {team_id}
        AND season = '{season}'
    """
    return run_query(query)

def get_top_players(team_id, season):
    query = f"""
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
    WHERE m.season = '{season}'
      AND ps.club_id = {team_id}
      AND ps.rating IS NOT NULL
    GROUP BY p.player_name
) t
ORDER BY avg_rating DESC;
"""
    return run_query(query)


def get_player_stats(player_id):
    query = f"""
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
                    (ps.club_id = m.home_club_id AND m.home_goals > m.away_goals) OR
                    (ps.club_id = m.away_club_id AND m.away_goals > m.home_goals)
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

        WHERE ps.player_id = {player_id}
        ORDER BY m.game_date DESC
    """
    return run_query(query)


def get_games(team_id, season):
    query = f"""
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
                WHEN m.home_club_id = {team_id} THEN 'home'
                ELSE 'away'
            END AS home_away,

            CASE
                WHEN m.home_club_id = {team_id} THEN away.club_name
                ELSE home.club_name
            END AS opponent

        FROM matches m
        JOIN clubs home
            ON m.home_club_id = home.club_id
        JOIN clubs away
            ON m.away_club_id = away.club_id
        WHERE m.season = '{season}'
          AND (m.home_club_id = {team_id} OR m.away_club_id = {team_id})
        ORDER BY m.game_date DESC
    """
    return run_query(query)


def get_match_search(match_id=None, team_a_id=None, team_b_id=None):
    if match_id is None and (team_a_id is None or team_b_id is None):
        return pd.DataFrame()

    where_clauses = []

    if match_id is not None:
        where_clauses.append(f"m.match_id = {match_id}")
    else:
        where_clauses.append(
            "(" \
            f"(m.home_club_id = {team_a_id} AND m.away_club_id = {team_b_id})" \
            " OR " \
            f"(m.home_club_id = {team_b_id} AND m.away_club_id = {team_a_id})" \
            ")"
        )

    where_sql = " AND ".join(where_clauses)

    query = f"""
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
    """
    return run_query(query)


def get_match_overview(match_id):
    query = f"""
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
        WHERE m.match_id = {match_id}
    """
    return run_query(query)


def get_match_player_stats(match_id):
    query = f"""
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
        WHERE ps.match_id = {match_id}
        ORDER BY c.club_name, p.player_name
    """
    return run_query(query)


def get_leagues_seasons():
        query = """
                SELECT DISTINCT league, season
                FROM matches
                WHERE league IS NOT NULL
                    AND season IS NOT NULL
                ORDER BY league, season DESC
        """
        return run_query(query)


def get_league_top_players(league, season, limit=50):
    query = f"""
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
        WHERE m.league = '{league}'
          AND m.season = '{season}'
          AND ps.rating IS NOT NULL
                GROUP BY p.player_name, c.club_name
                HAVING COUNT(ps.match_id) >= 10
        ORDER BY avg_rating DESC, games DESC
        LIMIT {int(limit)}
    """
    return run_query(query)


def _haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c


def get_clubs_in_radius(zip_code, radius_km=25):
    clubs_df = run_query(
        """
        SELECT club_id, club_name, plz, location
        FROM clubs
        WHERE plz IS NOT NULL
        """
    )

    postcodes_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "assets", "post-codes.csv")
    )
    postcodes_df = pd.read_csv(postcodes_path, dtype={"zip": str})
    postcodes_df = postcodes_df[["zip", "lat", "lng"]].dropna()
    postcodes_df["zip"] = postcodes_df["zip"].astype(str).str.strip()
    postcodes_df["lat"] = pd.to_numeric(postcodes_df["lat"], errors="coerce")
    postcodes_df["lng"] = pd.to_numeric(postcodes_df["lng"], errors="coerce")
    postcodes_df = postcodes_df.dropna().drop_duplicates(subset=["zip"], keep="first")

    zip_code_str = str(zip_code).strip()
    center_rows = postcodes_df[postcodes_df["zip"] == zip_code_str]
    if center_rows.empty:
        return pd.DataFrame()

    center_lat = float(center_rows.iloc[0]["lat"])
    center_lng = float(center_rows.iloc[0]["lng"])

    clubs_df["zip"] = clubs_df["plz"].astype(str).str.strip()
    merged_df = clubs_df.merge(postcodes_df, on="zip", how="left")
    merged_df = merged_df.dropna(subset=["lat", "lng"])

    merged_df["distance_km"] = merged_df.apply(
        lambda row: _haversine_km(center_lat, center_lng, float(row["lat"]), float(row["lng"])),
        axis=1,
    )

    result_df = merged_df[merged_df["distance_km"] <= float(radius_km)].copy()
    result_df = result_df.sort_values(["distance_km", "club_name"])
    result_df["distance_km"] = result_df["distance_km"].round(1)

    return result_df[["club_id", "club_name", "plz", "location", "distance_km"]]


def get_all_players_info():
    query = """
        SELECT 
            player_id, 
            player_name, 
            nationality, 
            date_of_birth, 
            height, 
            position, 
            prediction
        FROM players
        ORDER BY player_name
    """
    return run_query(query)

