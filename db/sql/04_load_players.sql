COPY player (player_id, player_name, nationality, date_of_birth, height, position)
FROM '/data/transform/player.csv'
WITH (FORMAT csv, HEADER true);