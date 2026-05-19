\ir /opt/db/sql/00_load_paths.sql

COPY players (player_id, player_name, nationality, date_of_birth, height, position, prediction)
FROM :'players_csv'
WITH (FORMAT csv, HEADER true);