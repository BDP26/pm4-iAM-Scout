COPY squad (player_id, club_id, season)
FROM '/data/squad.csv'
WITH (FORMAT csv, HEADER true);