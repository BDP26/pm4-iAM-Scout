import re
from bs4 import BeautifulSoup


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

