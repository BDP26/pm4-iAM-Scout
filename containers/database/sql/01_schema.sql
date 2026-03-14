    CREATE TABLE clubs (
        club_id INTEGER PRIMARY KEY,
        club_name TEXT NOT NULL,
        PLZ INTEGER,
        location TEXT
    );


    CREATE TABLE players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT NOT NULL,
        nationality TEXT,
        date_of_birth DATE,
        height NUMERIC(4,2),
        position TEXT
    );

    CREATE TABLE clubs_per_season (
        club_id INTEGER NOT NULL,
        league TEXT,
        season TEXT,
        PRIMARY KEY (club_id, season),
        FOREIGN KEY (club_id)
            REFERENCES clubs(club_id)
    );

    CREATE TABLE matches (
        match_id INTEGER PRIMARY KEY,
        season TEXT,
        game_date DATE,
        league TEXT,

        home_club_id INTEGER NOT NULL,
        away_club_id INTEGER NOT NULL,

        home_goals INTEGER CHECK (home_goals >= 0),
        away_goals INTEGER CHECK (away_goals >= 0),

        CHECK (home_club_id <> away_club_id),

        FOREIGN KEY (home_club_id, season)
            REFERENCES clubs_per_season(club_id, season),

        FOREIGN KEY (away_club_id, season)
            REFERENCES clubs_per_season(club_id, season)
    );

    CREATE INDEX idx_matches_home_club 
    ON matches(home_club_id);

    CREATE INDEX idx_matches_away_club 
    ON matches(away_club_id);

    CREATE INDEX idx_matches_season_league 
    ON matches(season, league);

    CREATE TABLE squads (
        player_id INTEGER,
        club_id INTEGER,
        season TEXT,

        PRIMARY KEY (player_id, club_id, season),

        FOREIGN KEY (player_id)
            REFERENCES players(player_id),

        FOREIGN KEY (club_id, season)
            REFERENCES clubs_per_season(club_id, season)
    );

    CREATE INDEX idx_squad_club_season 
    ON squad(club_id, season);

    CREATE TABLE player_stats (
        player_id INTEGER NOT NULL,
        match_id INTEGER NOT NULL,
        club_id INTEGER NOT NULL,

        goals INTEGER NOT NULL DEFAULT 0 CHECK (goals >= 0),
        assists INTEGER NOT NULL DEFAULT 0 CHECK (assists >= 0),

        yellow BOOLEAN NOT NULL DEFAULT FALSE,
        yellow_red BOOLEAN NOT NULL DEFAULT FALSE,
        red BOOLEAN NOT NULL DEFAULT FALSE,

        start_eleven BOOLEAN NOT NULL DEFAULT FALSE,

        minutes INTEGER NOT NULL DEFAULT 0 CHECK (minutes BETWEEN 0 AND 120),
        on_min INTEGER CHECK (on_min BETWEEN 0 AND 120),
        off_min INTEGER CHECK (off_min BETWEEN 0 AND 120),

        team_goals INTEGER NOT NULL DEFAULT 0 CHECK (team_goals >= 0),
        team_conceded INTEGER NOT NULL DEFAULT 0 CHECK (team_conceded >= 0),

        rating FLOAT,

        PRIMARY KEY (player_id, match_id),

        FOREIGN KEY (player_id) REFERENCES players(player_id),
        FOREIGN KEY (match_id) REFERENCES matches(match_id),
        FOREIGN KEY (club_id) REFERENCES clubs(club_id),

        CHECK (NOT (yellow_red AND NOT yellow)),
        CHECK (NOT (yellow_red AND red)),
        CHECK (NOT (start_eleven AND on_min > 0))
    );

    CREATE INDEX idx_player_stats_match
    ON player_stats(match_id)

    CREATE INDEX idx_player_stats_club
    ON player_stats(club_id);