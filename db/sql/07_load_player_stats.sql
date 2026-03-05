CREATE TEMP TABLE player_stats_tmp (
    player_id INTEGER,
    match_id INTEGER,
    club_id INTEGER,
    goals INTEGER,
    assists INTEGER,
    yellow INTEGER,
    yellow_red INTEGER,
    red INTEGER,
    start_11 INTEGER,
    minutes INTEGER,
    on_min TEXT,
    off_min TEXT,
    team_goals INTEGER,
    team_conceded INTEGER,
    result TEXT
);

COPY player_stats_tmp
FROM '/docker-entrypoint-initdb.d/player_stats.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO player_stats (
    player_id, match_id, club_id, season, goals, assists, 
    yellow, yellow_red, red, start_eleven, minutes, 
    on_min, off_min, team_goals_while_on_pitch, team_conceded_while_on_pitch
)
SELECT 
    ps.player_id,
    ps.match_id,
    ps.club_id,
    m.season,
    ps.goals,
    ps.assists,
    ps.yellow = 1,
    ps.yellow_red = 1,
    ps.red = 1,
    ps.start_11 = 1,
    ps.minutes,
    CASE WHEN ps.on_min = '' THEN NULL ELSE CAST(CAST(ps.on_min AS NUMERIC) AS INTEGER) END,
    CASE WHEN ps.off_min = '' THEN NULL ELSE CAST(CAST(ps.off_min AS NUMERIC) AS INTEGER) END,
    ps.team_goals,
    ps.team_conceded
FROM player_stats_tmp ps
JOIN matches m ON ps.match_id = m.match_id;