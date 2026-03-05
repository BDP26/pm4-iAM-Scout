-- Load players data from CSV
-- Expected CSV structure: player_id,player_name,nationality,date_of_birth,height,position

COPY player (player_id, player_name, nationality, date_of_birth, height, position)
FROM '/data/player.csv'
WITH (FORMAT csv, HEADER true);