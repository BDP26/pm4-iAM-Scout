from pathlib import Path

import pandas as pd

from web_scraping.transfermarkt.client import HttpClient
from web_scraping.transfermarkt.parser.players import PlayersParser
from web_scraping.toolkit.logger import Logger


class PlayersScraper:
    """Scraper for collecting player and squad information from Transfermarkt."""

    DESIRED_PLAYER_COLUMNS = [
        "player_id",
        "player_name",
        "nationality",
        "date_of_birth",
        "height",
        "position",
        "player_slug",
    ]

    def __init__(self, league_type="amateur"):
        """Initialize players scraper with league type."""
        self.base_url = "https://www.transfermarkt.ch"
        self.squad_url = "https://www.transfermarkt.ch/{club_slug}/kader/verein/{club_id}/saison_id/{season}"
        self.player_profile_url = "https://www.transfermarkt.ch/{player_slug}/profil/spieler/{player_id}"
        self.league_type = league_type

        self.project_root = Path(__file__).resolve().parents[3]
        self.data_dir = self.project_root / "data" / "scrape" / league_type

        self.clubs_path = self.data_dir / "clubs.csv"
        self.cps_path = self.data_dir / "clubs_per_season.csv"
        self.players_savepath = self.data_dir / "players.csv"
        self.squads_savepath = self.data_dir / "squads.csv"

        self.client = HttpClient()
        self.parser = PlayersParser()

    @staticmethod
    def _clean_id(value) -> str:
        """Clean and validate ID values from dataframes."""
        if value is None or pd.isna(value):
            return ""

        string_value = str(value).strip()
        if not string_value or string_value.lower() in {"nan", "<na>"}:
            return ""

        if string_value.endswith(".0"):
            string_value = string_value[:-2]

        return string_value

    def _make_absolute_url(self, href: str) -> str:
        """Convert relative URLs to absolute URLs."""
        href = (href or "").strip()
        if not href:
            return ""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if not href.startswith("/"):
            href = "/" + href
        return self.base_url + href

    def load_clubs(self):
        """Load club and season information from CSV files."""
        self.clubs_per_season = pd.read_csv(
            self.cps_path,
            dtype={"season": "int64", "club_id": "string", "league": "string"},
        )

        self.clubs = pd.read_csv(
            self.clubs_path,
            dtype={"club_name": "string", "club_id": "string", "club_slug": "string"},
        )

        self.clubs_per_season["club_id"] = self.clubs_per_season["club_id"].apply(self._clean_id)
        self.clubs["club_id"] = self.clubs["club_id"].apply(self._clean_id)
        self.clubs["club_slug"] = self.clubs["club_slug"].astype(str).str.strip()

        self.work = (
            self.clubs_per_season.merge(
                self.clubs[["club_id", "club_slug"]],
                on="club_id",
                how="left",
            )
            .drop_duplicates(subset=["season", "club_id"])
            .reset_index(drop=True)
        )

        missing_mask = self.work["club_id"].astype(str).str.strip() == ""
        if missing_mask.any():
            print("[WARN] Some clubs could not be mapped:")
            print(self.work.loc[missing_mask, ["season", "club_id"]].head(25).to_string(index=False))

        return self.work

    def collect_squads(self):
        """Collect squad membership and base player information."""
        if not hasattr(self, "work"):
            raise ValueError("Run load_clubs() first.")

        membership_rows = []
        self.base_players = {}

        empty_count = 0
        total_pages = 0
        not_found_count = 0

        for row in self.work.itertuples(index=False):
            season = int(row.season)
            club_id = self._clean_id(row.club_id)
            club_slug = str(row.club_slug or "").strip()

            if not club_id or not club_slug:
                continue

            url = self.squad_url.format(
                club_slug=club_slug,
                club_id=club_id,
                season=season,
            )

            try:
                html = self.client.get(url)
            except Exception as error:
                print(f"[WARN] squad page failed: club_id={club_id}, season={season}, url={url}, error={error}")
                not_found_count += 1
                continue

            total_pages += 1
            squad_players = self.parser.parse_squad_players(html)

            if not squad_players:
                empty_count += 1
                print(f"[INFO] Empty squad: club_id={club_id}, season={season}, url={url}")
                continue

            for player in squad_players:
                player_id = self._clean_id(player.get("player_id"))
                if not player_id:
                    continue

                membership_rows.append(
                    {
                        "player_id": player_id,
                        "club_id": club_id,
                        "season": season,
                    }
                )

                if player_id not in self.base_players:
                    self.base_players[player_id] = {
                        "player_id": player_id,
                        "player_slug": player.get("player_slug"),
                        "player_name": player.get("player_name"),
                        "player_href": player.get("player_href"),
                    }

        print(
            f"[INFO] Squad pages fetched: {total_pages}, "
            f"empty squads: {empty_count}, failed squads: {not_found_count}"
        )

        self.squads = (
            pd.DataFrame(membership_rows)
            .drop_duplicates(subset=["season", "club_id", "player_id"])
            .sort_values(["season", "club_id", "player_id"])
            .reset_index(drop=True)
        )

        if self.squads.empty:
            self.squads = pd.DataFrame(columns=["player_id", "club_id", "season"])
        else:
            self.squads = self.squads[["player_id", "club_id", "season"]]

        return self.squads

    def collect_player_profiles(self):
        """Collect player profile information including birth date, nationality, position."""
        if not hasattr(self, "base_players"):
            raise ValueError("Run collect_squads() first.")

        total_profiles = len(self.base_players)
        print(f"[INFO] Unique players to fetch profiles for: {total_profiles}")

        player_rows = []

        for index, (player_id, base_info) in enumerate(self.base_players.items(), start=1):
            if index % 100 == 0:
                print(f"[INFO] Profiles progress: {index}/{total_profiles}")

            player_details = {
                "birth_date": None,
                "nationality": None,
                "position": None,
                "height": None,
                "player_slug": None,
            }

            url = ""
            if base_info.get("player_href"):
                url = self._make_absolute_url(base_info["player_href"])

            if not url and base_info.get("player_slug"):
                url = self.player_profile_url.format(
                    player_slug=base_info["player_slug"],
                    player_id=player_id,
                )

            if url:
                try:
                    html = self.client.get(url)
                    parsed_details = self.parser.parse_player_profile(html)
                    if parsed_details:
                        player_details.update(parsed_details)

                    if player_details.get("player_slug"):
                        base_info["player_slug"] = player_details["player_slug"]

                except Exception as error:
                    print(f"[WARN] profile failed: player_id={player_id}, url={url}, error={error}")

            player_rows.append(
                {
                    "player_id": player_id,
                    "player_name": base_info.get("player_name"),
                    "nationality": player_details.get("nationality"),
                    "date_of_birth": player_details.get("birth_date"),
                    "height": player_details.get("height"),
                    "position": player_details.get("position"),
                    "player_slug": base_info.get("player_slug"),
                }
            )

        self.players = (
            pd.DataFrame(player_rows)
            .drop_duplicates(subset=["player_id"])
            .sort_values(["player_name", "player_id"], na_position="last")
            .reset_index(drop=True)
        )

        if self.players.empty:
            self.players = pd.DataFrame(columns=self.DESIRED_PLAYER_COLUMNS)
        else:
            for column in self.DESIRED_PLAYER_COLUMNS:
                if column not in self.players.columns:
                    self.players[column] = None
            self.players = self.players[self.DESIRED_PLAYER_COLUMNS]

        return self.players

    def _get_player_profile_urls(self, player_id: str) -> list[str]:
        """Generate candidate URLs for player profile pages."""
        player_id_clean = self._clean_id(player_id)
        return [
            f"{self.base_url}/-/profil/spieler/{player_id_clean}",
            f"{self.base_url}/profil/spieler/{player_id_clean}",
        ]

    def scrape_players_by_ids(self, player_ids) -> pd.DataFrame:
        """Scrape player profiles for a given list of player IDs."""
        if player_ids is None:
            raise ValueError("player_ids must not be None.")

        cleaned_ids = []
        seen_ids = set()

        for player_id_raw in player_ids:
            player_id = self._clean_id(player_id_raw)
            if not player_id or player_id in seen_ids:
                continue
            seen_ids.add(player_id)
            cleaned_ids.append(player_id)

        if not cleaned_ids:
            return pd.DataFrame(columns=self.DESIRED_PLAYER_COLUMNS)

        print(f"[INFO] Unique players to fetch: {len(cleaned_ids)}")

        player_rows = []

        for index, player_id in enumerate(cleaned_ids, start=1):
            if index % 50 == 0 or index == len(cleaned_ids):
                print(f"[INFO] Profiles progress: {index}/{len(cleaned_ids)}")

            player_details = {
                "player_name": None,
                "birth_date": None,
                "nationality": None,
                "position": None,
                "height": None,
                "player_slug": None,
            }

            last_error = None
            success = False

            for url in self._get_player_profile_urls(player_id):
                try:
                    html = self.client.get(url)
                    parsed_details = self.parser.parse_player_profile(html) or {}

                    has_data = any(
                        parsed_details.get(key)
                        for key in (
                            "player_name",
                            "birth_date",
                            "nationality",
                            "position",
                            "height",
                            "player_slug",
                        )
                    )

                    if has_data:
                        player_details.update(parsed_details)
                        success = True
                        break

                except Exception as error:
                    last_error = error

            if not success and last_error is not None:
                print(f"[WARN] profile failed: player_id={player_id}, error={last_error}")

            player_rows.append(
                {
                    "player_id": player_id,
                    "player_name": player_details.get("player_name"),
                    "nationality": player_details.get("nationality"),
                    "date_of_birth": player_details.get("birth_date"),
                    "height": player_details.get("height"),
                    "position": player_details.get("position"),
                    "player_slug": player_details.get("player_slug"),
                }
            )

        players_dataframe = pd.DataFrame(player_rows)

        if players_dataframe.empty:
            return pd.DataFrame(columns=self.DESIRED_PLAYER_COLUMNS)

        players_dataframe = (
            players_dataframe
            .drop_duplicates(subset=["player_id"])
            .sort_values(["player_name", "player_id"], na_position="last")
            .reset_index(drop=True)
        )

        for column in self.DESIRED_PLAYER_COLUMNS:
            if column not in players_dataframe.columns:
                players_dataframe[column] = None

        logger = Logger()
        logger.log(players_dataframe, "players")

        return players_dataframe[self.DESIRED_PLAYER_COLUMNS]

    def run(self):
        """Execute complete player and squad scraping workflow."""
        self.load_clubs()
        self.collect_squads()
        self.collect_player_profiles()

        logger = Logger()
        logger.log(self.players, "players")
        logger.log(self.squads, "squads")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.squads.to_csv(self.squads_savepath, index=False, encoding="utf-8-sig")
        self.players.to_csv(self.players_savepath, index=False, encoding="utf-8-sig")

        print(f"squads saved to: {self.squads_savepath}")
        print(f"players saved to: {self.players_savepath}")

        return self.squads, self.players


def main(league_type):
    """Execute players scraper with given league type."""
    scraper = PlayersScraper(league_type=league_type)
    scraper.run()


if __name__ == "__main__":
    main("amateur")