BEGIN;

CREATE TEMP TABLE staging_squads (
    player_id INTEGER,
    club_id INTEGER,
    season TEXT
) ON COMMIT DROP;

COPY staging_squads (player_id, club_id, season)
FROM '/data/transform/squads.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (player_id, club_id, season)
        player_id, club_id, season
    FROM staging_squads
    ORDER BY player_id, club_id, season
)
INSERT INTO squads (player_id, club_id, season)
SELECT player_id, club_id, season
FROM dedup
ON CONFLICT (player_id, club_id, season) DO NOTHING;

COMMIT;
