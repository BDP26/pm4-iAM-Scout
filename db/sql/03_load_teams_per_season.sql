-- Load teams_per_season data from CSV
-- Expected CSV structure: club_id,league,season

COPY team_per_season (club_id, league, season)
FROM '/data/teams_per_season.csv'
WITH (FORMAT csv, HEADER true);