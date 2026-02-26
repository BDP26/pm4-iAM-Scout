# web_scraping/club_locations.py
import re
import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from web_scraping.config import LOCATION_URL, STADIUM_URL
from web_scraping.transfermarkt import make_session, fetch_html

SLEEP_SECONDS = 1.5

def parse_plz_location(html):
    soup = BeautifulSoup(html, "lxml")

    facts_box = None
    for box in soup.select("div.box"):
        h2 = box.select_one("h2.content-box-headline")
        if h2 and "daten" in h2.get_text(strip=True).lower() and "fakten" in h2.get_text(strip=True).lower():
            facts_box = box
            break

    scope = facts_box if facts_box else soup

    for td in scope.select("table.profilheader td"):
        text = td.get_text(" ", strip=True).replace("\xa0", " ").strip()

        m = re.match(r"^(?:CH-)?(\d{4})\s+([^\(\n\r]+)", text)
        if m:
            plz = m.group(1).strip()
            location = m.group(2).strip()
            return plz, location

    return None, None

def parse_plz_location_stadium(html):

    soup = BeautifulSoup(html, "lxml")

    contact_box = None
    for box in soup.select("div.box"):
        h2 = box.select_one("h2.content-box-headline")
        if h2 and h2.get_text(strip=True).lower() == "kontakt":
            contact_box = box
            break

    scope = contact_box if contact_box else soup

    for td in scope.select("table.profilheader td"):
        text = td.get_text(" ", strip=True).replace("\xa0", " ").strip()
        m = re.match(r"^(?:CH-)?(\d{4})\s+(.+)$", text)
        if m:
            plz = m.group(1).strip()
            location = m.group(2).strip()
            return plz, location

    text = scope.get_text("\n", strip=True).replace("\xa0", " ")
    m = re.search(r"\b(?:CH-)?(\d{4})\s+([A-Za-zÀ-ÿ'’\-\.\s]+)\b", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return None, None

def get_locations(teams_unique: pd.DataFrame) -> pd.DataFrame:
    required = {"club_id", "club_slug"}
    missing = required - set(teams_unique.columns)
    if missing:
        raise ValueError(f"teams_unique is missing columns: {missing}")

    session = make_session()
    df = teams_unique.copy()

    plz_list: list[Optional[str]] = []
    location_list: list[Optional[str]] = []

    for _, row in df.iterrows():
        club_id = str(row["club_id"]).strip()
        slug = str(row["club_slug"]).strip()

        plz = location = None

        url_facts = LOCATION_URL.format(slug=slug, club_id=club_id)
        try:
            html = fetch_html(session, url_facts)
            plz, location = parse_plz_location(html)
        except Exception:
            pass

        if not (plz and location):
            url_stadium = STADIUM_URL.format(slug=slug, club_id=club_id)
            try:
                html = fetch_html(session, url_stadium)
                plz, location = parse_plz_location_stadium(html)
            except Exception:
                pass

        plz_list.append(plz)
        location_list.append(location)

        time.sleep(SLEEP_SECONDS)

    df["PLZ"] = plz_list
    df["location"] = location_list
    return df

def main() -> None:
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    inp = output_dir / "teams_unique.csv"
    out = output_dir / "teams_unique_with_locations.csv"

    teams_unique = pd.read_csv(inp, dtype={"club_id": "string"})
    enriched = get_locations(teams_unique)
    enriched.to_csv(out, index=False, encoding="utf-8")

    missing = enriched[enriched["PLZ"].isna() | enriched["location"].isna()]
    print(f"Saved: {out}")
    print(f"Missing locations: {len(missing)} / {len(enriched)}")

if __name__ == "__main__":
    main()