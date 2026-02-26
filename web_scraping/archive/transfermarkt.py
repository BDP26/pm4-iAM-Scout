# web_scraping/transfermarkt.py
import re
import requests
from bs4 import BeautifulSoup

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
    })
    return s

def parse_clubs(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.items")
    if table is None:
        raise ValueError("Table 'table.items' not found (blocked/error page/HTML changed).")

    clubs = []
    for row in table.select("tbody > tr"):
        a = row.select_one("td.hauptlink a")
        if not a:
            continue

        name = re.sub(r"\s+", " ", a.get_text(strip=True))
        href = a.get("href", "")

        m = re.search(r"/verein/(\d+)", href)
        club_id = m.group(1) if m else None

        m_slug = re.search(r"^/([^/]+)/", href)
        club_slug = m_slug.group(1) if m_slug else None

        clubs.append({"club_name": name, "club_id": club_id, "club_slug": club_slug})


    return clubs

def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text