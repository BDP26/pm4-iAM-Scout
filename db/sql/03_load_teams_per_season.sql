CREATE TEMP TABLE teams_per_season_tmp (
    season TEXT,
    league TEXT,
    club_id INTEGER
);

COPY teams_per_season_tmp
FROM '/docker-entrypoint-initdb.d/teams_per_season.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO team_per_season (club_id, league, season)
SELECT club_id, league, season
FROM teams_per_season_tmp;