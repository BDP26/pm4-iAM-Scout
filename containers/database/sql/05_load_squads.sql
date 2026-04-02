\ir /opt/db/sql/00_load_paths.sql

COPY squads (player_id, club_id, season)
FROM :'squads_csv'
WITH (FORMAT csv, HEADER true);