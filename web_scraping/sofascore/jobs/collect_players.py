from __future__ import annotations

from pathlib import Path

import pandas as pd

from web_scraping.config import PRO_SEASONS
from web_scraping.sofascore.client import SofaScoreClient
from web_scraping.sofascore.parser.players import (
    parse_player_profile,
    parse_players_from_stats_page,
)
from web_scraping.write_csv import write_pro_players


def _clean_id(x) -> str:
    if x is None or pd.isna(x):
        return ""
    s = str(x).strip()
    if not s or s.lower() in {"nan", "<na>"}:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s


def collect_pro_players() -> pd.DataFrame:
    player_index: dict[str, dict] = {}

    client = SofaScoreClient()
    try:
        for season_id, season_label in PRO_SEASONS.items():
            print(f"[INFO] Fetch stats pages for season={season_label}, season_id={season_id}")

            try:
                html_pages = client.get_stats_pages(season_id)
            except Exception as e:
                print(
                    f"[WARN] stats pages failed: season={season_label}, "
                    f"season_id={season_id}: {e}"
                )
                continue

            print(f"[INFO] Stats HTML pages fetched: {len(html_pages)}")

            all_parsed_rows: list[dict] = []

            for page_no, html in enumerate(html_pages, start=1):
                if page_no == 1:
                    debug_path = Path.cwd() / f"debug_stats_{season_id}_page_1.html"
                    debug_path.write_text(html, encoding="utf-8")
                    print(f"[DEBUG] Saved first stats HTML to: {debug_path}")

                parsed_rows = parse_players_from_stats_page(html)
                print(
                    f"[INFO] Parsed player rows page={page_no}: {len(parsed_rows)} "
                    f"for season={season_label}"
                )
                all_parsed_rows.extend(parsed_rows)

            deduped: dict[str, dict] = {}
            for row in all_parsed_rows:
                player_id = _clean_id(row.get("player_id"))
                if not player_id:
                    continue
                if player_id not in deduped:
                    deduped[player_id] = {
                        "player_id": player_id,
                        "player_name": row.get("player_name"),
                        "player_slug": row.get("player_slug"),
                    }

            print(f"[INFO] Parsed player rows total deduped: {len(deduped)}")

            for player_id, row in deduped.items():
                if player_id not in player_index:
                    player_index[player_id] = {
                        "player_id": player_id,
                        "player_name": row.get("player_name"),
                        "date_of_birth": None,
                        "height": None,
                        "position": None,
                        "player_slug": row.get("player_slug"),
                    }

        print(f"[INFO] Unique players to enrich: {len(player_index)}")

        for i, (pid, base) in enumerate(player_index.items(), start=1):
            if i % 50 == 0 or i == len(player_index):
                print(f"[INFO] Profiles progress: {i}/{len(player_index)}")

            slug = (base.get("player_slug") or "").strip()
            if not slug:
                continue

            try:
                html = client.get_player_profile(slug, pid)
                parsed = parse_player_profile(html)
                if parsed:
                    base["date_of_birth"] = parsed.get("birth_date")
                    base["height"] = parsed.get("height")
                    base["position"] = parsed.get("position")
                    if parsed.get("canonical_slug"):
                        base["player_slug"] = parsed["canonical_slug"]
            except Exception as e:
                print(f"[WARN] player profile failed: player_id={pid}, slug={slug}: {e}")

    finally:
        client.close()

    if player_index:
        players = (
            pd.DataFrame(player_index.values())
            .drop_duplicates(subset=["player_id"])
            .sort_values(["player_name", "player_id"])
            .reset_index(drop=True)
        )
    else:
        players = pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "date_of_birth",
                "height",
                "position",
                "player_slug",
            ]
        )

    desired_cols = [
        "player_id",
        "player_name",
        "date_of_birth",
        "height",
        "position",
        "player_slug",
    ]
    for c in desired_cols:
        if c not in players.columns:
            players[c] = None

    return players[desired_cols]


def main() -> None:
    out_dir = Path(__file__).resolve().parents[3] / "data/scrape/pro"
    players = collect_pro_players()
    p = write_pro_players(players, output_dir=out_dir)
    print(f"Saved: {p}")


if __name__ == "__main__":
    main()