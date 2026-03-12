import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from web_scraping.config import START_YEAR, END_YEAR, MATCHES_URLS, SLEEP_SECONDS, get_scrape_output_dir
from web_scraping.write_csv import write_matches
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.matches import parse_matches

today = datetime.now(ZoneInfo("Europe/Zurich")).date()


def collect_matches() -> pd.DataFrame:
    seasons = list(range(START_YEAR, END_YEAR))
    session = make_session()

    all_rows: list[dict] = []

    for league, url_tpl in MATCHES_URLS.items():
        for season in seasons:
            url = url_tpl.format(season=season)
            html = fetch_html(session, url)

            parsed = parse_matches(html)
            for m in parsed:
                all_rows.append(
                    {
                        "match_id": m["match_id"],
                        "season": season,
                        "date": m["datum"],
                        "league": league,
                        "home_club_id": m["home_club_id"],
                        "away_club_id": m["away_club_id"],
                        "home_goals": m["score_home"],
                        "away_goals": m["score_away"],
                    }
                )

            time.sleep(SLEEP_SECONDS)

    df = (
        pd.DataFrame(all_rows)
        .drop_duplicates(subset=["match_id"])
        .sort_values(["season", "league", "date", "match_id"], na_position="last")
        .reset_index(drop=True)
    )

    df["_date_dt"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = (
        df[df["_date_dt"].notna() & (df["_date_dt"] <= today)]
        .drop(columns=["_date_dt"])
        .reset_index(drop=True)
    )

    cols = [
        "match_id",
        "season",
        "date",
        "league",
        "home_club_id",
        "away_club_id",
        "home_goals",
        "away_goals",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols]
    return df


def main() -> None:
    out_dir = get_scrape_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    matches = collect_matches()
    p = write_matches(matches, output_dir=out_dir)
    print(f"Saved: {p}")


if __name__ == "__main__":
    main()