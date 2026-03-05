CREATE TEMP TABLE matches_tmp (
    match_id INTEGER,
    season TEXT,
    datum TEXT,
    liga TEXT,
    heimmannschaft INTEGER,
    gastmannschaft INTEGER,
    score_home NUMERIC,
    score_away NUMERIC,
    result TEXT
);

COPY matches_tmp
FROM '/docker-entrypoint-initdb.d/matches.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO matches (match_id, season, game_date, league, home_club_id, away_club_id, home_goals, away_goals)
SELECT 
    match_id,
    season,
    TO_DATE(datum, 'YYYY-MM-DD'),
    liga,
    heimmannschaft,
    gastmannschaft,
    CAST(score_home AS INTEGER),
    CAST(score_away AS INTEGER)
FROM matches_tmp;