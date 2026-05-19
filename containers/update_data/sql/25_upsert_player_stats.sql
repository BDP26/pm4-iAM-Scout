BEGIN;

CREATE TEMP TABLE staging_player_stats (
    player_id INTEGER,
    match_id INTEGER,
    club_id INTEGER,
    goals INTEGER,
    assists INTEGER,
    yellow BOOLEAN,
    yellow_red BOOLEAN,
    red BOOLEAN,
    start_eleven BOOLEAN,
    minutes INTEGER,
    on_min INTEGER,
    off_min INTEGER,
    team_goals INTEGER,
    team_conceded INTEGER,
    rating DOUBLE PRECISION
) ON COMMIT DROP;

COPY staging_player_stats (
    player_id, match_id, club_id, goals, assists,
    yellow, yellow_red, red, start_eleven,
    minutes, on_min, off_min, team_goals, team_conceded, rating
)
FROM '/data/transform/player_stats.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (player_id, match_id)
        player_id, match_id, club_id, goals, assists,
        yellow, yellow_red, red, start_eleven,
        minutes, on_min, off_min, team_goals, team_conceded, rating
    FROM staging_player_stats
    ORDER BY player_id, match_id
)
INSERT INTO player_stats (
    player_id, match_id, club_id, goals, assists,
    yellow, yellow_red, red, start_eleven,
    minutes, on_min, off_min, team_goals, team_conceded, rating
)
SELECT
    player_id, match_id, club_id, goals, assists,
    yellow, yellow_red, red, start_eleven,
    minutes, on_min, off_min, team_goals, team_conceded, rating
FROM dedup
ON CONFLICT (player_id, match_id) DO UPDATE
SET club_id = EXCLUDED.club_id,
    goals = EXCLUDED.goals,
    assists = EXCLUDED.assists,
    yellow = EXCLUDED.yellow,
    yellow_red = EXCLUDED.yellow_red,
    red = EXCLUDED.red,
    start_eleven = EXCLUDED.start_eleven,
    minutes = EXCLUDED.minutes,
    on_min = EXCLUDED.on_min,
    off_min = EXCLUDED.off_min,
    team_goals = EXCLUDED.team_goals,
    team_conceded = EXCLUDED.team_conceded,
    rating = EXCLUDED.rating;

COMMIT;
