BEGIN;

CREATE TEMP TABLE staging_clubs_per_season (
    club_id INTEGER,
    league TEXT,
    season TEXT
) ON COMMIT DROP;

COPY staging_clubs_per_season (club_id, league, season)
FROM '/data/transform/clubs_per_season.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (club_id, season)
        club_id, league, season
    FROM staging_clubs_per_season
    ORDER BY club_id, season
)
INSERT INTO clubs_per_season (club_id, league, season)
SELECT club_id, league, season
FROM dedup
ON CONFLICT (club_id, season) DO UPDATE
SET league = EXCLUDED.league;

COMMIT;

