import re
from bs4 import BeautifulSoup

_RE_PLAYER_ID = re.compile(r"/spieler/(\d+)")
_RE_SLUG = re.compile(r"^/([^/]+)/")
_RE_BIRTH_AND_AGE = re.compile(r"(\d{2}\.\d{2}\.\d{4})(?:\s*\((\d+)\))?")
_RE_PROFILE = re.compile(r"(?:\\/|/)([^\\/]+)(?:\\/|/)profil(?:\\/|/)spieler(?:\\/|/)(\d+)")
_RE_SPIELER = re.compile(r"(?:\\/|/)spieler(?:\\/|/)(\d+)")

def parse_squad_players(html: str) -> list[dict]:
    players: list[dict] = []
    seen: set[str] = set()

    matches = _RE_PROFILE.findall(html)
    if matches:
        soup = BeautifulSoup(html, "lxml")
        name_by_id: dict[str, str] = {}
        for a in soup.select('a[href*="profil"][href*="spieler"]'):
            href = (a.get("href") or "").strip()
            m = _RE_PROFILE.search(href)
            if not m:
                continue
            pid = m.group(2)
            txt = a.get_text(" ", strip=True)
            if txt:
                name_by_id.setdefault(pid, txt)

        for slug, pid in matches:
            if pid in seen:
                continue
            seen.add(pid)
            players.append(
                {
                    "player_id": pid,
                    "player_slug": slug,
                    "player_name": name_by_id.get(pid),
                    "player_href": f"/{slug}/profil/spieler/{pid}",
                }
            )
        return players

    ids = list(dict.fromkeys(_RE_SPIELER.findall(html)))
    if ids:
        return [
            {"player_id": pid, "player_slug": None, "player_name": None, "player_href": None}
            for pid in ids
        ]

    return []



def parse_player_profile(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    canonical_slug = None
    canon = soup.select_one('link[rel="canonical"]')
    if canon:
        href = (canon.get("href") or "").strip()
        m = _RE_SLUG.search(href.replace("https://www.transfermarkt.ch", ""))
        if m:
            canonical_slug = m.group(1)

    birth_date = None
    age = None
    birth_el = soup.select_one('span[itemprop="birthDate"]')
    if birth_el:
        txt = birth_el.get_text(" ", strip=True)
        m = _RE_BIRTH_AND_AGE.search(txt)
        if m:
            birth_date = m.group(1)
            if m.group(2):
                age = int(m.group(2))

    nationality = None
    nat_el = soup.select_one('span[itemprop="nationality"]')
    if nat_el:
        flags = []
        for img in nat_el.select("img"):
            t = (img.get("title") or img.get("alt") or "").strip()
            if t:
                flags.append(t)
        if flags:
            nationality = "; ".join(dict.fromkeys(flags))
        else:
            nationality = nat_el.get_text(" ", strip=True) or None

    height = None
    h_el = soup.select_one('span[itemprop="height"]')
    if h_el:
        height = h_el.get_text(" ", strip=True) or None

    position = None
    for li in soup.select("li.data-header__label"):
        label = li.get_text(" ", strip=True).lower()
        if "position" in label:
            content = li.select_one("span.data-header__content")
            if content:
                position = content.get_text(" ", strip=True) or None
            break

    return {
        "birth_date": birth_date,
        "age": age,
        "nationality": nationality,
        "position": position,
        "height": height,
        "canonical_slug": canonical_slug,
    }