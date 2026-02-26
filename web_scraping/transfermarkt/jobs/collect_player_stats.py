from __future__ import annotations
import time
from pathlib import Path
import pandas as pd

from web_scraping.config import START_YEAR, END_YEAR, PLAYER_STAT_URL, SLEEP_SECONDS
from web_scraping.output.write_csv import write_player_stats
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.player_stat import (
    parse_player_leistungsdaten,
    parse_spielbericht_goals,
    parse_spielbericht_player_sub_minutes,
    derive_start11_onoff,
)

BASE_URL = "https://www.transfermarkt.ch"


def _abs_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href.startswith("/"):
        href = "/" + href
    return BASE_URL + href


def _result_for_team(score_home: int | None, score_away: int | None, team_is_home: bool) -> str | None:
    if score_home is None or score_away is None:
        return None
    if score_home == score_away:
        return "draw"
    if team_is_home:
        return "win" if score_home > score_away else "loss"
    return "win" if score_away > score_home else "loss"


def collect_player_stats() -> pd.DataFrame:
    out_dir = Path(__file__).resolve().parents[2] / "output"

    players = pd.read_csv(out_dir / "players.csv", dtype={"player_id": "string", "player_slug": "string"})
    matches = pd.read_csv(
        out_dir / "matches.csv",
        dtype={
            "match_id": "string",
            "heimmannschaft": "string",
            "gastmannschaft": "string",
            "score_home": "Int64",
            "score_away": "Int64",
        },
    )

    match_info = {
        str(r.match_id): {
            "home": str(r.heimmannschaft),
            "away": str(r.gastmannschaft),
            "sh": None if pd.isna(r.score_home) else int(r.score_home),
            "sa": None if pd.isna(r.score_away) else int(r.score_away),
        }
        for r in matches.itertuples(index=False)
    }
    match_ids_set = set(match_info.keys())

    session = make_session()

    match_html_cache: dict[str, str] = {}
    goals_cache: dict[str, list[tuple[int, str]]] = {}

    rows: list[dict] = []
    seasons = list(range(START_YEAR, END_YEAR))

    players = players.dropna(subset=["player_id", "player_slug"]).copy()

    for season in seasons:
        for p in players.itertuples(index=False):
            player_id = str(p.player_id).strip()
            slug = str(p.player_slug).strip()
            if not player_id or not slug:
                continue

            url = PLAYER_STAT_URL.format(slug=slug, player_id=player_id, season=season)
            html = fetch_html(session, url)
            stats_rows = parse_player_leistungsdaten(html)

            time.sleep(SLEEP_SECONDS)

            for s in stats_rows:
                match_id = str(s["match_id"])
                if match_id not in match_ids_set:
                    continue  # nur Spiele, die in matches.csv sind

                club_id = (s.get("club_id") or "").strip()
                if not club_id:
                    continue

                mi = match_info[match_id]
                home_id, away_id = mi["home"], mi["away"]
                if club_id != home_id and club_id != away_id:
                    continue  # falscher Wettbewerb/Club

                team_is_home = (club_id == home_id)
                result = _result_for_team(mi["sh"], mi["sa"], team_is_home)

                minutes_played = s.get("minuten")
                if minutes_played is None or int(minutes_played) <= 0:
                    continue  # hat nicht gespielt

                # Matchreport laden (1x pro match_id)
                if match_id not in match_html_cache:
                    href = s.get("match_href") or ""
                    match_url = _abs_url(href)
                    mh = fetch_html(session, match_url)
                    match_html_cache[match_id] = mh
                    time.sleep(SLEEP_SECONDS)

                mh = match_html_cache[match_id]

                # goals cached
                if match_id not in goals_cache:
                    goals_cache[match_id] = parse_spielbericht_goals(mh)
                goals = goals_cache[match_id]

                sub_mins = parse_spielbericht_player_sub_minutes(mh, player_id)
                start_11, on_min, off_min = derive_start11_onoff(int(minutes_played), sub_mins)

                team_goals = sum(1 for minute, cid in goals if on_min <= minute <= off_min and cid == club_id)
                team_conceded = sum(1 for minute, cid in goals if on_min <= minute <= off_min and cid != club_id)

                rows.append(
                    {
                        "player_id": player_id,
                        "match_id": match_id,
                        "club_id": club_id,
                        "goals": int(s.get("tore") or 0),
                        "assists": int(s.get("assists") or 0),
                        "yellow": int(s.get("gelb") or 0),
                        "yellow_red": int(s.get("gelb_rot") or 0),
                        "red": int(s.get("rot") or 0),
                        "start_11": int(start_11),
                        "minutes": int(minutes_played),
                        "on_min": int(on_min),
                        "off_min": int(off_min),
                        "team_goals": int(team_goals),
                        "team_conceded": int(team_conceded),
                        "result": result,
                    }
                )

    df = pd.DataFrame(rows).drop_duplicates(subset=["player_id", "match_id"]).reset_index(drop=True)

    cols = [
        "player_id",
        "match_id",
        "club_id",
        "goals",
        "assists",
        "yellor",
        "yellow_red",
        "red",
        "start_11",
        "minutes",
        "on_min",
        "off_min",
        "team_goals",
        "team_conceded",
        "result",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]


def main() -> None:
    out_dir = Path(__file__).resolve().parents[2] / "output"
    df = collect_player_stats()
    p = write_player_stats(df, output_dir=out_dir)
    print(f"Saved: {p}")


if __name__ == "__main__":
    main()