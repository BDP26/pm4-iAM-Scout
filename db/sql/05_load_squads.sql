CREATE TEMP TABLE squads_tmp (
    season TEXT,
    club_id INTEGER,
    player_id INTEGER
);

COPY squads_tmp
FROM '/docker-entrypoint-initdb.d/squads.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO squad (player_id, club_id, season)
SELECT player_id, club_id, season
FROM squads_tmp;