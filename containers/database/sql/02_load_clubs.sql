\ir /opt/db/sql/00_load_paths.sql

COPY clubs (club_id, club_name, PLZ, location)
FROM :'clubs_csv'
WITH (FORMAT csv, HEADER true);