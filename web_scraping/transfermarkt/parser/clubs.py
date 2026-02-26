import re
from bs4 import BeautifulSoup


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

        if not club_id or not club_slug:
            continue

        clubs.append({"club_name": name, "club_id": club_id, "club_slug": club_slug})

    return clubs