from __future__ import annotations
import time
import pandas as pd

from web_scraping.config import START_YEAR, END_YEAR, PLAYER_STAT_URL, SLEEP_SECONDS, get_scrape_output_dir
from web_scraping.write_csv import write_player_stats
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.player_stats import (
    parse_player_leistungsdaten,
    parse_spielbericht_goals,
    parse_spielbericht_player_sub_events,
    derive_start11_onoff_and_intervals,
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





def _minute_in_intervals(minute: int, intervals: list[tuple[int, int | None]]) -> bool:
    for start, end in intervals:
        off_excl = 10**9 if end is None else int(end)
        if int(start) <= int(minute) < off_excl:
            return True
    return False


def collect_player_stats() -> pd.DataFrame:
    out_dir = get_scrape_output_dir()

    players = pd.read_csv(out_dir / "player.csv", dtype={"player_id": "string", "player_slug": "string"})
    matches = pd.read_csv(
        out_dir / "matches.csv",
        dtype={
            "match_id": "string",
            "home_club_id": "string",
            "away_club_id": "string",
            "home_goals": "Int64",
            "away_goals": "Int64",
        },
    )

    match_info = {
        str(r.match_id): {
            "home": str(r.home_club_id),
            "away": str(r.away_club_id),
            "sh": None if pd.isna(r.home_goals) else int(r.home_goals),
            "sa": None if pd.isna(r.away_goals) else int(r.away_goals),
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
                    continue

                club_id = (s.get("club_id") or "").strip()
                if not club_id:
                    continue

                mi = match_info[match_id]
                home_id, away_id = mi["home"], mi["away"]
                if club_id != home_id and club_id != away_id:
                    continue

                team_is_home = club_id == home_id

                minutes_played = s.get("minuten")
                if minutes_played is None or int(minutes_played) <= 0:
                    continue

                if match_id not in match_html_cache:
                    href = s.get("match_href") or ""
                    match_url = _abs_url(href)
                    mh = fetch_html(session, match_url)
                    match_html_cache[match_id] = mh
                    time.sleep(SLEEP_SECONDS)

                mh = match_html_cache[match_id]

                if match_id not in goals_cache:
                    goals_cache[match_id] = parse_spielbericht_goals(mh)
                goals = goals_cache[match_id]

                sub_events = parse_spielbericht_player_sub_events(mh, player_id)
                start_eleven, on_min_eff, off_min_eff, intervals = derive_start11_onoff_and_intervals(
                    int(minutes_played),
                    sub_events,
                )

                on_min_out = None if start_eleven == 1 else int(on_min_eff)
                off_min_out = None if off_min_eff is None else int(off_min_eff)

                team_goals = sum(
                    1
                    for minute, cid in goals
                    if cid == club_id and _minute_in_intervals(int(minute), intervals)
                )
                team_conceded = sum(
                    1
                    for minute, cid in goals
                    if cid != club_id and _minute_in_intervals(int(minute), intervals)
                )

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
                        "start_eleven": int(start_eleven),
                        "minutes": int(minutes_played),
                        "on_min": on_min_out,
                        "off_min": off_min_out,
                        "team_goals": int(team_goals),
                        "team_conceded": int(team_conceded),
                    }
                )

    df = pd.DataFrame(rows).drop_duplicates(subset=["player_id", "match_id"]).reset_index(drop=True)

    cols = [
        "player_id",
        "match_id",
        "club_id",
        "goals",
        "assists",
        "yellow",
        "yellow_red",
        "red",
        "start_eleven",
        "minutes",
        "on_min",
        "off_min",
        "team_goals",
        "team_conceded",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]


def main() -> None:
    player_stats = collect_player_stats()
    p = write_player_stats(player_stats)
    print(f"Saved: {p}")


if __name__ == "__main__":
    main()