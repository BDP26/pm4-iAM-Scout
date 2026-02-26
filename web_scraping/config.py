SLEEP_SECONDS = 0.5

START_YEAR = 2025
END_YEAR = 2026

LEAGUE_URLS = {
    "pl": "https://www.transfermarkt.ch/promotion-league/tabelle/wettbewerb/CHPR?saison_id={season}"#,
    #"1_liga_gr_1": "https://www.transfermarkt.ch/1-liga-gruppe-1/tabelle/wettbewerb/CHC1/saison_id/{season}",
    #"1_liga_gr_2": "https://www.transfermarkt.ch/1-liga-gruppe-2/tabelle/wettbewerb/CHC2/saison_id/{season}",
    #"1_liga_gr_3": "https://www.transfermarkt.ch/1-liga-gruppe-3/tabelle/wettbewerb/CHC3/saison_id/{season}",
}

LOCATION_URL = "https://www.transfermarkt.ch/{slug}/datenfakten/verein/{club_id}"
STADIUM_URL   = "https://www.transfermarkt.ch/{slug}/stadion/verein/{club_id}"

SQUAD_URL = "https://www.transfermarkt.ch/{slug}/kader/verein/{club_id}/saison_id/{season}"
PLAYER_PROFILE_URL = "https://www.transfermarkt.ch/{player_slug}/profil/spieler/{player_id}"

MATCHES_URLS = {
    "pl": "https://www.transfermarkt.ch/promotion-league/gesamtspielplan/wettbewerb/CHPR/saison_id/{season}"
}

PLAYER_STAT_URL = "https://www.transfermarkt.ch/{slug}/leistungsdaten/spieler/{player_id}/plus/0?saison={season}"
