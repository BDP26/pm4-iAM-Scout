\ir /opt/db/sql/00_load_paths.sql

COPY clubs_per_season (club_id, league, season)
FROM :'clubs_per_season_csv'
WITH (FORMAT csv, HEADER true);