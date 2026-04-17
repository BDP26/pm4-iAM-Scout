BEGIN;

CREATE TEMP TABLE staging_players (
    player_id INTEGER,
    player_name TEXT,
    nationality TEXT,
    date_of_birth DATE,
    height NUMERIC(4,2),
    position TEXT
) ON COMMIT DROP;

COPY staging_players (player_id, player_name, nationality, date_of_birth, height, position)
FROM '/data/transform/players.csv'
WITH (FORMAT csv, HEADER true);

WITH dedup AS (
    SELECT DISTINCT ON (player_id)
        player_id, player_name, nationality, date_of_birth, height, position
    FROM staging_players
    ORDER BY player_id
)
INSERT INTO players (player_id, player_name, nationality, date_of_birth, height, position)
SELECT player_id, player_name, nationality, date_of_birth, height, position
FROM dedup
ON CONFLICT (player_id) DO UPDATE
SET player_name = EXCLUDED.player_name,
    nationality = EXCLUDED.nationality,
    date_of_birth = EXCLUDED.date_of_birth,
    height = EXCLUDED.height,
    position = EXCLUDED.position;

COMMIT;

