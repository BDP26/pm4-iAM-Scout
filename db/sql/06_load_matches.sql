COPY matches (match_id, season, game_date, league, home_club_id, away_club_id, home_goals, away_goals)
FROM '/data/matches.csv'
WITH (FORMAT csv, HEADER true);