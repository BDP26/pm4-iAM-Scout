COPY player_stats (player_id, match_id, club_id, goals, assists, yellow, yellow_red, red, start_eleven, minutes, on_min, off_min, team_goals_while_on_pitch, team_conceded_while_on_pitch, season)
FROM '/data/player_stats.csv'
WITH (FORMAT csv, HEADER true);