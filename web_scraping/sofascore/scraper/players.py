from __future__ import annotations

from pathlib import Path

import pandas as pd

from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.players import SofaScorePlayersParser


class SofaScorePlayersScraper:
    DEFAULT_SEASON_URLS: dict[str, str] = {
        "25/26": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:77152,tab:stats",
        "24/25": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:61658,tab:stats",
        "23/24": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:52366,tab:stats",
        "22/23": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:42276,tab:stats",
        "21/22": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:37158,tab:stats"
        "20/21": "https://www.sofascore.com/football/tournament/switzerland/super-league/215#id:32512,tab:stats"
    }

    def __init__(
        self,
        seasons: list[str] | None = None,
        client: SofaScoreClient | None = None,
    ) -> None:
        self.seasons = seasons or ["25/26", "24/25"]
        self.players_savepath = "data/scrape/pro/players_sofascore.csv"
        self.client = client or SofaScoreClient()
        self.parser = SofaScorePlayersParser()
        self.season_ids: dict[str, str] = dict(self.DEFAULT_SEASON_URLS)

    @staticmethod
    def _clean_id(x) -> str:
        if x is None or pd.isna(x):
            return ""

        s = str(x).strip()
        if not s or s.lower() in {"nan", "<na>"}:
            return ""

        if s.endswith(".0"):
            s = s[:-2]

        return s

    def _save_players(self, players: pd.DataFrame) -> Path:
        savepath = Path(self.players_savepath)
        savepath.parent.mkdir(parents=True, exist_ok=True)
        players.to_csv(savepath, index=False)
        return savepath

    def _build_players_df(self, player_index: dict[str, dict]) -> pd.DataFrame:
        if player_index:
            players = (
                pd.DataFrame(player_index.values())
                .drop_duplicates(subset=["id"])
                .sort_values(["name", "id"], na_position="last")
                .reset_index(drop=True)
            )
        else:
            players = pd.DataFrame(columns=["name", "id", "slug"])

        for col in ["name", "id", "slug"]:
            if col not in players.columns:
                players[col] = None

        return players[["name", "id", "slug"]]

    def _resolve_season_id(self, season: str) -> str:
        if season not in self.season_ids:
            raise ValueError(
                f"Season '{season}' nicht in self.season_ids vorhanden. "
                f"Bekannt: {list(self.season_ids.keys())}"
            )

        value = str(self.season_ids[season]).strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError(
                f"season_ids[{season!r}] muss eine vollständige SofaScore-Stats-URL sein. "
                f"Erhalten: {value!r}"
            )

        return value

    def run(self) -> pd.DataFrame:
        player_index: dict[str, dict] = {}

        try:
            for season_label in self.seasons:
                season_id = self._resolve_season_id(season_label)

                print(
                    f"[INFO] Fetch stats pages for season={season_label}, "
                    f"season_id={season_id}"
                )

                try:
                    html_pages = self.client.get_stats_pages(season_id)
                except Exception as e:
                    print(
                        f"[WARN] stats pages failed: season={season_label}, "
                        f"season_id={season_id}: {e}"
                    )
                    continue

                print(f"[INFO] Stats HTML pages fetched: {len(html_pages)}")

                all_parsed_rows: list[dict] = []

                for page_no, html in enumerate(html_pages, start=1):
                    parsed_rows = self.parser.parse_players_from_stats_page(html)
                    print(
                        f"[INFO] Parsed player rows page={page_no}: {len(parsed_rows)} "
                        f"for season={season_label}"
                    )
                    all_parsed_rows.extend(parsed_rows)

                deduped: dict[str, dict] = {}
                for row in all_parsed_rows:
                    player_id = self._clean_id(row.get("id"))
                    if not player_id:
                        continue

                    if player_id not in deduped:
                        deduped[player_id] = {
                            "id": player_id,
                            "name": row.get("name"),
                            "slug": row.get("slug"),
                        }

                print(f"[INFO] Parsed player rows total deduped: {len(deduped)}")

                for player_id, row in deduped.items():
                    if player_id not in player_index:
                        player_index[player_id] = {
                            "id": player_id,
                            "name": row.get("name"),
                            "slug": row.get("slug"),
                        }
                    else:
                        if not player_index[player_id].get("name") and row.get("name"):
                            player_index[player_id]["name"] = row.get("name")
                        if not player_index[player_id].get("slug") and row.get("slug"):
                            player_index[player_id]["slug"] = row.get("slug")

            print(f"[INFO] Unique players to enrich: {len(player_index)}")

            for i, (pid, base) in enumerate(player_index.items(), start=1):
                if i % 50 == 0 or i == len(player_index):
                    print(f"[INFO] Profiles progress: {i}/{len(player_index)}")

                slug = (base.get("slug") or "").strip()
                if not slug:
                    continue

                try:
                    html = self.client.get_player_profile(slug, pid)
                    parsed = self.parser.parse_player_profile(html)

                    if parsed and parsed.get("canonical_slug"):
                        base["slug"] = parsed["canonical_slug"]
                except Exception as e:
                    print(f"[WARN] player profile failed: player_id={pid}, slug={slug}: {e}")

        finally:
            self.client.close()

        players = self._build_players_df(player_index)
        savepath = self._save_players(players)
        print(f"Saved: {savepath}")

        return players


def main() -> None:
    scraper = SofaScorePlayersScraper(seasons=["25/26", "24/25"])
    scraper.run()


if __name__ == "__main__":
    main()