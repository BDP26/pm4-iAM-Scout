BEGIN;

CREATE TEMP TABLE staging_clubs (
    club_id INTEGER,
    club_name TEXT,
    PLZ INTEGER,
    location TEXT
) ON COMMIT DROP;

COPY staging_clubs (club_id, club_name, PLZ, location)
FROM '/data/transform/clubs.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (club_id)
        club_id, club_name, PLZ, location
    FROM staging_clubs
    ORDER BY club_id
)
INSERT INTO clubs (club_id, club_name, PLZ, location)
SELECT club_id, club_name, PLZ, location
FROM dedup
ON CONFLICT (club_id) DO UPDATE
SET club_name = EXCLUDED.club_name,
    PLZ = EXCLUDED.PLZ,
    location = EXCLUDED.location;

COMMIT;
