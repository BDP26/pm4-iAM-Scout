BEGIN;

CREATE TEMP TABLE staging_matches (
    match_id INTEGER,
    season TEXT,
    league TEXT,
    game_date DATE,
    home_club_id INTEGER,
    away_club_id INTEGER,
    home_goals INTEGER,
    away_goals INTEGER
) ON COMMIT DROP;

COPY staging_matches (match_id, season, league, game_date, home_club_id, away_club_id, home_goals, away_goals)
FROM '/data/transform/matches.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (match_id)
        match_id, season, league, game_date, home_club_id, away_club_id, home_goals, away_goals
    FROM staging_matches
    ORDER BY match_id
)
INSERT INTO matches (
    match_id, season, game_date, league,
    home_club_id, away_club_id, home_goals, away_goals
)
SELECT
    match_id, season, game_date, league,
    home_club_id, away_club_id, home_goals, away_goals
FROM dedup
ON CONFLICT (match_id) DO UPDATE
SET season = EXCLUDED.season,
    game_date = EXCLUDED.game_date,
    league = EXCLUDED.league,
    home_club_id = EXCLUDED.home_club_id,
    away_club_id = EXCLUDED.away_club_id,
    home_goals = EXCLUDED.home_goals,
    away_goals = EXCLUDED.away_goals;

COMMIT;
