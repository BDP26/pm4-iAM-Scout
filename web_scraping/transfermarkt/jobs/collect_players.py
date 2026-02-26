# web_scraping/transfermarkt/jobs/collect_players.py

import random
import time
from pathlib import Path

import pandas as pd
import requests

from web_scraping.config import PLAYER_PROFILE_URL, SQUAD_URL
from web_scraping.output.write_csv import write_players, write_roster_memberships
from web_scraping.transfermarkt.client import fetch_html, make_session
from web_scraping.transfermarkt.parser.players import parse_player_profile, parse_squad_players

SLEEP_SECONDS = 0.5
BASE_URL = "https://www.transfermarkt.ch"

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_PROFILE_TRIES = 3


def _abs_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href.startswith("/"):
        href = "/" + href
    return BASE_URL + href


def _clean_id(x) -> str:
    if x is None or pd.isna(x):
        return ""
    s = str(x).strip()
    if not s or s.lower() in {"nan", "<na>"}:
        return ""
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _fetch_profile_with_retries(session, url: str) -> str | None:
    for attempt in range(1, MAX_PROFILE_TRIES + 1):
        try:
            return fetch_html(session, url)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None

            if code in RETRY_STATUS_CODES and attempt < MAX_PROFILE_TRIES:
                backoff = (2**attempt) + random.uniform(0, 0.7)
                print(
                    f"[WARN] profile {code} attempt {attempt}/{MAX_PROFILE_TRIES} -> retry in {backoff:.1f}s | {url}"
                )
                time.sleep(backoff)
                continue

            print(f"[WARN] profile http error pid=? url={url}: {e}")
            return None
        except Exception as e:
            if attempt < MAX_PROFILE_TRIES:
                backoff = (2**attempt) + random.uniform(0, 0.7)
                print(
                    f"[WARN] profile error attempt {attempt}/{MAX_PROFILE_TRIES} -> retry in {backoff:.1f}s | {url} | {e}"
                )
                time.sleep(backoff)
                continue
            print(f"[WARN] profile failed url={url}: {e}")
            return None

    return None


def collect_players_and_squads(
    teams_per_season: pd.DataFrame,
    teams_unique: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    req_tps = {"season", "club_id"}
    req_tu = {"club_id", "club_id", "club_slug"}
    if not req_tps.issubset(teams_per_season.columns):
        raise ValueError(f"teams_per_season missing columns: {req_tps - set(teams_per_season.columns)}")
    if not req_tu.issubset(teams_unique.columns):
        raise ValueError(f"teams_unique missing columns: {req_tu - set(teams_unique.columns)}")

    tps = teams_per_season.copy()
    tu = teams_unique.copy()
    tps["club_id"] = tps["club_id"].astype(str).str.strip()
    tu["club_id"] = tu["club_id"].astype(str).str.strip()

    tu["club_id"] = tu["club_id"].apply(_clean_id)
    tu["club_slug"] = tu["club_slug"].astype(str).str.strip()

    work = (
        tps.merge(tu[["club_id", "club_slug"]], on="club_id", how="left")
        .drop_duplicates(subset=["season", "club_id"])
        .reset_index(drop=True)
    )

    missing_mask = (work["club_id"].isna()) | (work["club_id"].astype(str).str.strip() == "")
    if missing_mask.any():
        examples = work.loc[missing_mask, ["season", "club_id"]].head(25)
        print("[WARN] Some clubs could not be mapped to club_id via club_name. Examples:")
        print(examples.to_string(index=False))

    session = make_session()

    membership_rows: list[dict] = []
    base_players: dict[str, dict] = {}  # player_id -> base info

    empty_count = 0
    total_pages = 0
    not_found_count = 0

    for row in work.itertuples(index=False):
        season = int(getattr(row, "season"))
        club_id = _clean_id(getattr(row, "club_id"))
        club_slug = str(getattr(row, "club_slug") or "").strip()

        if not club_id or not club_slug:
            continue

        url = SQUAD_URL.format(slug=club_slug, club_id=club_id, season=season)

        try:
            html = fetch_html(session, url)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                not_found_count += 1
                print(f"[WARN] 404 squad page (skip): club_id={club_id}, season={season}, url={url}")
                time.sleep(SLEEP_SECONDS)
                continue
            raise

        total_pages += 1

        squad_players = parse_squad_players(html)

        if not squad_players:
            empty_count += 1
            print(f"[INFO] Empty squad: club_id={club_id}, season={season}, url={url}")
            time.sleep(SLEEP_SECONDS)
            continue

        for p in squad_players:
            pid = _clean_id(p.get("player_id"))
            if not pid:
                continue

            membership_rows.append({"season": season, "club_id": club_id, "player_id": pid})

            if pid not in base_players:
                base_players[pid] = {
                    "player_id": pid,
                    "player_slug": p.get("player_slug"),
                    "player_name": p.get("player_name"),
                    "player_href": p.get("player_href"),
                }

        time.sleep(SLEEP_SECONDS)

    print(f"[INFO] Squad pages fetched: {total_pages}, empty squads: {empty_count}, 404 squads: {not_found_count}")

    roster_memberships = (
        pd.DataFrame(membership_rows)
        .drop_duplicates(subset=["season", "club_id", "player_id"])
        .sort_values(["season", "club_id", "player_id"])
        .reset_index(drop=True)
    )

    total_profiles = len(base_players)
    print(f"[INFO] Unique players to fetch profiles for: {total_profiles}")

    player_rows: list[dict] = []

    for i, (pid, base) in enumerate(base_players.items(), start=1):
        if i % 100 == 0:
            print(f"[INFO] Profiles progress: {i}/{total_profiles}")

        url = ""
        if base.get("player_href"):
            url = _abs_url(base["player_href"])

        if not url and base.get("player_slug"):
            url = PLAYER_PROFILE_URL.format(player_slug=base["player_slug"], player_id=pid)

        details = {
            "birth_date": None,
            "age": None,
            "nationality": None,
            "position": None,
            "height": None,
            "canonical_slug": None,
        }

        if url:
            html = _fetch_profile_with_retries(session, url)
            if html:
                parsed = parse_player_profile(html)
                if parsed:
                    details.update(parsed)

                canonical = details.get("canonical_slug")
                if canonical:
                    base["player_slug"] = canonical

        time.sleep(SLEEP_SECONDS)

        player_rows.append(
            {
                "player_name": base.get("player_name"),
                "player_slug": base.get("player_slug"),
                "player_id": pid,
                "geburtsdatum": details.get("birth_date"),
                "alter": details.get("age"),
                "nationalitaet": details.get("nationality"),
                "position": details.get("position"),
                "groesse": details.get("height"),
            }
        )

    players = (
        pd.DataFrame(player_rows)
        .drop_duplicates(subset=["player_id"])
        .sort_values(["player_name", "player_id"])
        .reset_index(drop=True)
    )

    desired_cols = [
        "player_name",
        "player_slug",
        "player_id",
        "geburtsdatum",
        "alter",
        "nationalitaet",
        "position",
        "groesse",
    ]
    for c in desired_cols:
        if c not in players.columns:
            players[c] = None
    players = players[desired_cols]

    return roster_memberships, players


def main() -> None:
    out_dir = Path(__file__).resolve().parents[2] / "output"

    teams_per_season = pd.read_csv(
        out_dir / "teams_per_season.csv",
        dtype={"season": "int64", "club_id": "string", "league": "string"},
    )
    teams_unique = pd.read_csv(
        out_dir / "teams_unique.csv",
        dtype={"club_name": "string", "club_id": "string", "club_slug": "string"},
    )

    teams_unique["club_id"] = teams_unique["club_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    roster_memberships, players = collect_players_and_squads(teams_per_season, teams_unique)

    p1 = write_roster_memberships(roster_memberships, output_dir=out_dir)
    p2 = write_players(players, output_dir=out_dir)
    print(f"Saved: {p1}")
    print(f"Saved: {p2}")


if __name__ == "__main__":
    main()