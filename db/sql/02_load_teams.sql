COPY teams (club_id, club_name, PLZ, city)
FROM '/data/teams.csv'
WITH (FORMAT csv, HEADER true);