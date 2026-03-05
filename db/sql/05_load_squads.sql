-- Load squad data from CSV
-- Expected CSV structure: player_id,club_id,season

COPY squad (player_id, club_id, season)
FROM '/data/squad.csv'
WITH (FORMAT csv, HEADER true);