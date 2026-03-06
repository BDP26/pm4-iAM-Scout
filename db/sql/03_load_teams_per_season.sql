COPY team_per_season (club_id, league, season)
FROM '/data/teams_per_season.csv'
WITH (FORMAT csv, HEADER true);