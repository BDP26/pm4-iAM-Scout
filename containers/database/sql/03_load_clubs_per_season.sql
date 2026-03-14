COPY team_per_season (club_id, league, season)
FROM '/data/transform/team_per_season.csv'
WITH (FORMAT csv, HEADER true);