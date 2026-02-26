import re
from datetime import datetime
from bs4 import BeautifulSoup


_RE_MATCH = re.compile(r"/([^/]+)/.*?/spielbericht/(\d+)")
_RE_CLUB_ID = re.compile(r"/verein/(\d+)")
_RE_SCORE = re.compile(r"(\d+)\s*:\s*(\d+)")
_RE_DATE = re.compile(r"(\d{2}[./]\d{2}[./]\d{2,4})")


def _to_iso_date(text: str) -> str | None:
    if not text:
        return None
    m = _RE_DATE.search(text)
    if not m:
        return None
    s = m.group(1).replace(".", "/")
    dd, mm, yy = s.split("/")
    if len(yy) == 2:
        yy = "20" + yy
    try:
        return datetime(int(yy), int(mm), int(dd)).date().isoformat()
    except ValueError:
        return None


def _first_two_unique(xs: list[str]) -> tuple[str, str] | None:
    seen = set()
    out = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
        if len(out) == 2:
            return out[0], out[1]
    return None


def parse_matches(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    anchors = soup.select('a[href*="spielbericht/"]')
    if not anchors:
        title = (soup.title.get_text(strip=True) if soup.title else "NO_TITLE")
        snippet = soup.get_text(" ", strip=True)[:300]
        raise ValueError(f"No spielbericht links found. title={title!r} snippet={snippet!r}")

    rows = []
    last_date_iso: str | None = None
    seen_match_ids = set()

    for a in anchors:
        href = a.get("href") or ""
        m = _RE_MATCH.search(href)
        if not m:
            continue

        match_slug, match_id = m.group(1), m.group(2)
        if match_id in seen_match_ids:
            continue
        seen_match_ids.add(match_id)

        container = a.find_parent("tr") or a.find_parent("li") or a.find_parent("div") or a.parent
        container_html = str(container)

        club_ids = _RE_CLUB_ID.findall(container_html)
        pair = _first_two_unique(club_ids)
        if not pair:
            continue
        home_id, away_id = pair

        text = container.get_text(" ", strip=True)
        date_iso = _to_iso_date(text) or last_date_iso
        if date_iso:
            last_date_iso = date_iso

        score_home = None
        score_away = None
        score_text = a.get_text(" ", strip=True)
        ms = _RE_SCORE.search(score_text) or _RE_SCORE.search(text)
        if ms:
            score_home = int(ms.group(1))
            score_away = int(ms.group(2))

        rows.append(
            dict(
                match_id=match_id,
                match_slug=match_slug,
                datum=date_iso,
                home_club_id=home_id,
                away_club_id=away_id,
                score_home=score_home,
                score_away=score_away,
            )
        )

    return rows