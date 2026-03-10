SLEEP_SECONDS = 0.5

START_YEAR = 2024
END_YEAR = 2025

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

GAMEMINUTE_IMAGES = {
    "-0px -0px": 1,
    "-36px -0px": 2,
    "-72px -0px": 3,
    "-108px -0px": 4,
    "-144px -0px": 5,
    "-180px -0px": 6,
    "-216px -0px": 7,
    "-252px -0px": 8,
    "-288px -0px": 9,
    "-324px -0px": 10,

    "-0px -36px": 11,
    "-36px -36px": 12,
    "-72px -36px": 13,
    "-108px -36px": 14,
    "-144px -36px": 15,
    "-180px -36px": 16,
    "-216px -36px": 17,
    "-252px -36px": 18,
    "-288px -36px": 19,
    "-324px -36px": 20,

    "-0px -72px": 21,
    "-36px -72px": 22,
    "-72px -72px": 23,
    "-108px -72px": 24,
    "-144px -72px": 25,
    "-180px -72px": 26,
    "-216px -72px": 27,
    "-252px -72px": 28,
    "-288px -72px": 29,
    "-324px -72px": 30,

    "-0px -108px": 31,
    "-36px -108px": 32,
    "-72px -108px": 33,
    "-108px -108px": 34,
    "-144px -108px": 35,
    "-180px -108px": 36,
    "-216px -108px": 37,
    "-252px -108px": 38,
    "-288px -108px": 39,
    "-324px -108px": 40,

    "-0px -144px": 41,
    "-36px -144px": 42,
    "-72px -144px": 43,
    "-108px -144px": 44,
    "-144px -144px": 45,
    "-180px -144px": 46,
    "-216px -144px": 47,
    "-252px -144px": 48,
    "-288px -144px": 49,
    "-324px -144px": 50,

    "-0px -180px": 51,
    "-36px -180px": 52,
    "-72px -180px": 53,
    "-108px -180px": 54,
    "-144px -180px": 55,
    "-180px -180px": 56,
    "-216px -180px": 57,
    "-252px -180px": 58,
    "-288px -180px": 59,
    "-324px -180px": 60,

    "-0px -216px": 61,
    "-36px -216px": 62,
    "-72px -216px": 63,
    "-108px -216px": 64,
    "-144px -216px": 65,
    "-180px -216px": 66,
    "-216px -216px": 67,
    "-252px -216px": 68,
    "-288px -216px": 69,
    "-324px -216px": 70,

    "-0px -252px": 71,
    "-36px -252px": 72,
    "-72px -252px": 73,
    "-108px -252px": 74,
    "-144px -252px": 75,
    "-180px -252px": 76,
    "-216px -252px": 77,
    "-252px -252px": 78,
    "-288px -252px": 79,
    "-324px -252px": 80,

    "-0px -288px": 81,
    "-36px -288px": 82,
    "-72px -288px": 83,
    "-108px -288px": 84,
    "-144px -288px": 85,
    "-180px -288px": 86,
    "-216px -288px": 87,
    "-252px -288px": 88,
    "-288px -288px": 89,
    "-324px -288px": 90,
}