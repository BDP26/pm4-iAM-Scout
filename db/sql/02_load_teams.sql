CREATE TEMP TABLE teams_tmp (
    club_name TEXT,
    club_id INTEGER,
    club_slug TEXT,
    plz INTEGER,
    city TEXT
);

COPY teams_tmp
FROM '/docker-entrypoint-initdb.d/teams.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO teams (club_id, club_name, plz, city)
SELECT club_id, club_name, plz, city
FROM teams_tmp;