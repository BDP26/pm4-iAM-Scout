COPY squad (player_id, club_id, season)
FROM '/data/transform/squad.csv'
WITH (FORMAT csv, HEADER true);