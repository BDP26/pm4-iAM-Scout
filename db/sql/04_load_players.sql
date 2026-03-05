CREATE TEMP TABLE players_tmp (
    player_name TEXT,
    player_slug TEXT,
    player_id INTEGER,
    geburtsdatum TEXT,
    alter INTEGER,
    nationalitaet TEXT,
    position TEXT,
    groesse TEXT
);

COPY players_tmp
FROM '/docker-entrypoint-initdb.d/players.csv'
WITH (
    FORMAT csv,
    HEADER true
);

INSERT INTO player (player_id, player_name, nationality, date_of_birth, height, position)
SELECT 
    player_id,
    player_name,
    CASE WHEN nationalitaet = '' THEN NULL ELSE nationalitaet END,
    CASE 
        WHEN geburtsdatum ~ '^\d{2}\.\d{2}\.\d{4}$' THEN 
            TO_DATE(geburtsdatum, 'DD.MM.YYYY')
        ELSE NULL 
    END,
    CASE 
        WHEN groesse ~ '^\d+,\d+\s*m$' THEN 
            CAST(REPLACE(SUBSTRING(groesse FROM '^\d+,\d+'), ',', '.') AS NUMERIC(4,2))
        ELSE NULL 
    END,
    CASE WHEN position = '' THEN NULL ELSE position END
FROM players_tmp;