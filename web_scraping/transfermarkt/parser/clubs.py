import re
from bs4 import BeautifulSoup


class ClubsParser:
    def __init__(self, parser: str = "lxml"):
        self.parser = parser

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, self.parser)

    def parse_clubs(self, html: str) -> list[dict]:
        soup = self._soup(html)
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

            clubs.append(
                {
                    "club_name": name,
                    "club_id": club_id,
                    "club_slug": club_slug,
                }
            )

        return clubs

    def parse_plz_location(self, html: str) -> tuple[str | None, str | None]:
        soup = self._soup(html)

        facts_box = None
        for box in soup.select("div.box"):
            h2 = box.select_one("h2.content-box-headline")
            if h2:
                headline = h2.get_text(strip=True).lower()
                if "daten" in headline and "fakten" in headline:
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

    def parse_plz_location_stadium(self, html: str) -> tuple[str | None, str | None]:
        soup = self._soup(html)

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