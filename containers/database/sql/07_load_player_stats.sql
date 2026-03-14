COPY player_stats (player_id, match_id, club_id, goals, assists, yellow, yellow_red, red, start_eleven, minutes, on_min, off_min, team_goals, team_conceded, rating)
FROM '/data/transform/player_stats.csv'
WITH (FORMAT csv, HEADER true);