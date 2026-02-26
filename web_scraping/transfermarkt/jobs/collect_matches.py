import time
from pathlib import Path
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from web_scraping.config import START_YEAR, END_YEAR, MATCHES_URLS
from web_scraping.output.write_csv import write_matches
from web_scraping.transfermarkt.client import make_session, fetch_html
from web_scraping.transfermarkt.parser.matches import parse_matches

today = datetime.now(ZoneInfo("Europe/Zurich")).date()

SLEEP_SECONDS = 0.5

def _result(score_home, score_away) -> str | None:
    if score_home is None or score_away is None:
        return None
    if score_home == score_away:
        return "draw"
    return "win_home" if score_home > score_away else "win_away"

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
                        "datum": m["datum"],
                        "liga": league,
                        "heimmannschaft": m["home_club_id"],
                        "gastmannschaft": m["away_club_id"],
                        "score_home": m["score_home"],
                        "score_away": m["score_away"],
                        "result": _result(m["score_home"], m["score_away"]),
                    }
                )

            time.sleep(SLEEP_SECONDS)

    df = (
        pd.DataFrame(all_rows)
        .drop_duplicates(subset=["match_id"])
        .sort_values(["season", "liga", "datum", "match_id"], na_position="last")
        .reset_index(drop=True)
    )

    df["_datum_dt"] = pd.to_datetime(df["datum"], errors="coerce").dt.date
    df = df[df["_datum_dt"].notna() & (df["_datum_dt"] <= today)].drop(columns=["_datum_dt"]).reset_index(drop=True)

    cols = [
        "match_id", "season", "datum", "liga",
        "heimmannschaft", "gastmannschaft",
        "score_home", "score_away", "result",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]

    return df

def main() -> None:
    out_dir = Path(__file__).resolve().parents[2] / "output"
    matches = collect_matches()
    p = write_matches(matches, output_dir=out_dir)
    print(f"Saved: {p}")

if __name__ == "__main__":
    main()