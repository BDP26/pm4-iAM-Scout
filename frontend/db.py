import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

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
    
    
