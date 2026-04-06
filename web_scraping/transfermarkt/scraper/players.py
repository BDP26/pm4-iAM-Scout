from pathlib import Path
import pandas as pd

from web_scraping.transfermarkt.parser.players import PlayersParser
from web_scraping.transfermarkt.client import HttpClient
from web_scraping.toolkit.logger import Logger


class PlayersScraper:
    def __init__(self, league_type="amateur"):
        self.base_url = "https://www.transfermarkt.ch"
        self.squad_url = "https://www.transfermarkt.ch/{club_slug}/kader/verein/{club_id}/saison_id/{season}"
        self.player_profile_url = "https://www.transfermarkt.ch/{player_slug}/profil/spieler/{player_id}"
        self.league_type = league_type

        self.clubs_path = f"data/scrape/{league_type}/clubs.csv"
        self.cps_path = f"data/scrape/{league_type}/clubs_per_season.csv"

        self.players_savepath = f"data/scrape/{league_type}/players.csv"
        self.squads_savepath = f"data/scrape/{league_type}/squads.csv"

        self.client = HttpClient()
        self.parser = PlayersParser()

    def _abs_url(self, href: str) -> str:
        href = (href or "").strip()
        if not href:
            return ""
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if not href.startswith("/"):
            href = "/" + href
        return self.base_url + href

    def _clean_id(self, x) -> str:
        if x is None or pd.isna(x):
            return ""

        s = str(x).strip()
        if not s or s.lower() in {"nan", "<na>"}:
            return ""

        if s.endswith(".0"):
            s = s[:-2]

        return s

    def load_clubs(self):
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
            except Exception as e:
                print(f"[WARN] squad page failed: club_id={club_id}, season={season}, url={url}, error={e}")
                not_found_count += 1
                continue

            total_pages += 1
            squad_players = self.parser.parse_squad_players(html)

            if not squad_players:
                empty_count += 1
                print(f"[INFO] Empty squad: club_id={club_id}, season={season}, url={url}")
                continue

            for p in squad_players:
                pid = self._clean_id(p.get("player_id"))
                if not pid:
                    continue

                membership_rows.append(
                    {
                        "player_id": pid,
                        "club_id": club_id,
                        "season": season,
                    }
                )

                if pid not in self.base_players:
                    self.base_players[pid] = {
                        "player_id": pid,
                        "player_slug": p.get("player_slug"),
                        "player_name": p.get("player_name"),
                        "player_href": p.get("player_href"),
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
        if not hasattr(self, "base_players"):
            raise ValueError("Run collect_squads() first.")

        total_profiles = len(self.base_players)
        print(f"[INFO] Unique players to fetch profiles for: {total_profiles}")

        player_rows = []

        for i, (pid, base) in enumerate(self.base_players.items(), start=1):
            if i % 100 == 0:
                print(f"[INFO] Profiles progress: {i}/{total_profiles}")

            url = ""
            if base.get("player_href"):
                url = self._abs_url(base["player_href"])

            if not url and base.get("player_slug"):
                url = self.player_profile_url.format(
                    player_slug=base["player_slug"],
                    player_id=pid,
                )

            details = {
                "birth_date": None,
                "nationality": None,
                "position": None,
                "height": None,
                "player_slug": None,
            }

            if url:
                try:
                    html = self.client.get(url)
                    parsed = self.parser.parse_player_profile(html)
                    if parsed:
                        details.update(parsed)

                    if details.get("player_slug"):
                        base["player_slug"] = details["player_slug"]

                except Exception as e:
                    print(f"[WARN] profile failed: player_id={pid}, url={url}, error={e}")

            player_rows.append(
                {
                    "player_id": pid,
                    "player_name": base.get("player_name"),
                    "nationality": details.get("nationality"),
                    "date_of_birth": details.get("birth_date"),
                    "height": details.get("height"),
                    "position": details.get("position"),
                    "player_slug": base.get("player_slug"),
                }
            )

        self.players = (
            pd.DataFrame(player_rows)
            .drop_duplicates(subset=["player_id"])
            .sort_values(["player_name", "player_id"], na_position="last")
            .reset_index(drop=True)
        )

        desired_cols = [
            "player_id",
            "player_name",
            "nationality",
            "date_of_birth",
            "height",
            "position",
            "player_slug",
        ]

        if self.players.empty:
            self.players = pd.DataFrame(columns=desired_cols)
        else:
            for c in desired_cols:
                if c not in self.players.columns:
                    self.players[c] = None
            self.players = self.players[desired_cols]

        return self.players

    def _player_profile_url_candidates(self, player_id: str) -> list[str]:
        pid = self._clean_id(player_id)
        return [
            f"{self.base_url}/-/profil/spieler/{pid}",
            f"{self.base_url}/profil/spieler/{pid}",
        ]

    def scrape_players_by_ids(self, player_ids) -> pd.DataFrame:
        if player_ids is None:
            raise ValueError("player_ids must not be None.")

        cleaned_ids = []
        seen = set()

        for x in player_ids:
            pid = self._clean_id(x)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            cleaned_ids.append(pid)

        desired_cols = [
            "player_id",
            "player_name",
            "nationality",
            "date_of_birth",
            "height",
            "position",
            "player_slug",
        ]

        if not cleaned_ids:
            return pd.DataFrame(columns=desired_cols)

        print(f"[INFO] Unique players to fetch: {len(cleaned_ids)}")

        player_rows = []

        for i, pid in enumerate(cleaned_ids, start=1):
            if i % 50 == 0 or i == len(cleaned_ids):
                print(f"[INFO] Profiles progress: {i}/{len(cleaned_ids)}")

            details = {
                "player_name": None,
                "birth_date": None,
                "nationality": None,
                "position": None,
                "height": None,
                "player_slug": None,
            }

            last_error = None
            success = False

            for url in self._player_profile_url_candidates(pid):
                try:
                    html = self.client.get(url)
                    parsed = self.parser.parse_player_profile(html) or {}

                    has_data = any(
                        parsed.get(k)
                        for k in (
                            "player_name",
                            "birth_date",
                            "nationality",
                            "position",
                            "height",
                            "player_slug",
                        )
                    )

                    if has_data:
                        details.update(parsed)
                        success = True
                        break

                except Exception as e:
                    last_error = e

            if not success and last_error is not None:
                print(f"[WARN] profile failed: player_id={pid}, error={last_error}")

            player_rows.append(
                {
                    "player_id": pid,
                    "player_name": details.get("player_name"),
                    "nationality": details.get("nationality"),
                    "date_of_birth": details.get("birth_date"),
                    "height": details.get("height"),
                    "position": details.get("position"),
                    "player_slug": details.get("player_slug"),
                }
            )

        players = pd.DataFrame(player_rows)

        if players.empty:
            return pd.DataFrame(columns=desired_cols)

        players = (
            players
            .drop_duplicates(subset=["player_id"])
            .sort_values(["player_name", "player_id"], na_position="last")
            .reset_index(drop=True)
        )

        for c in desired_cols:
            if c not in players.columns:
                players[c] = None

        return players[desired_cols]

    def run(self):
        self.load_clubs()
        self.collect_squads()
        self.collect_player_profiles()

        logger = Logger()
        logger.log(self.players, "players")
        logger.log(self.squads, "squads")

        self.squads.to_csv(self.squads_savepath, index=False, encoding="utf-8-sig")
        self.players.to_csv(self.players_savepath, index=False, encoding="utf-8-sig")

        print(f"squads saved to: {self.squads_savepath}")
        print(f"players saved to: {self.players_savepath}")

        return self.squads, self.players


def main(league_type):
    scraper = PlayersScraper(
        league_type=league_type
    )
    scraper.run()


if __name__ == "__main__":
    main("amateur")