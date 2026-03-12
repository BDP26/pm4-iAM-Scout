COPY teams (club_id, club_name, PLZ, location)
FROM '/data/transform/teams.csv'
WITH (FORMAT csv, HEADER true);