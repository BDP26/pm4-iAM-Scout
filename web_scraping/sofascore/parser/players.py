from __future__ import annotations

from datetime import datetime
import re

from bs4 import BeautifulSoup


_PLAYER_RE = re.compile(r'/football/player/([^/"\'?#]+)/(\d+)')
_TEAM_RE = re.compile(r'/football/team/([^/"\'?#]+)/(\d+)')
_TITLE_RE = re.compile(r'title="([^"]+)"')



def _clean_text(x: str | None) -> str | None:
    if x is None:
        return None
    x = re.sub(r"\s+", " ", x).strip()
    return x or None


def _parse_players_dom(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    players: list[dict] = []
    seen: set[str] = set()

    candidate_links = soup.select('a[href*="/football/player/"]')

    for a in candidate_links:
        href = (a.get("href") or "").strip()
        pm = _PLAYER_RE.search(href)
        if not pm:
            continue

        player_slug, player_id = pm.group(1), pm.group(2)
        if player_id in seen:
            continue

        player_name = _clean_text(a.get_text(" ", strip=True))
        if not player_name:
            continue

        row = a.find_parent("tr")
        if row is None:
            row = a.find_parent("div")
        if row is None:
            continue

        # nur echte Tabellen-/Listenzeilen übernehmen:
        # entweder es gibt einen Team-Link oder title-Fallback im selben Row-Container
        team_a = row.select_one('a[href*="/football/team/"]')
        team_td = row.select_one("td[title]")

        if team_a is None and team_td is None:
            continue

        seen.add(player_id)
        players.append(
            {
                "player_id": player_id,
                "player_slug": player_slug,
                "player_name": player_name,
            }
        )

    return players


def _parse_players_regex(html: str) -> list[dict]:
    players: list[dict] = []
    seen: set[str] = set()

    for m in re.finditer(r'/football/player/[^"\'<> ]+/\d+', html):
        start = max(0, m.start() - 1200)
        end = min(len(html), m.end() + 1200)
        chunk = html[start:end]

        # nur Chunks mit Team-Hinweis akzeptieren, sonst fangen wir irrelevante Links
        if "/football/team/" not in chunk and 'title="' not in chunk:
            continue

        pm = _PLAYER_RE.search(chunk)
        if not pm:
            continue

        player_slug, player_id = pm.group(1), pm.group(2)
        if player_id in seen:
            continue

        player_name = None

        anchor_match = re.search(
            rf'href="[^"]*/football/player/{re.escape(player_slug)}/{player_id}"[^>]*>([^<]+)</a>',
            chunk,
        )
        if anchor_match:
            player_name = _clean_text(anchor_match.group(1))

        if not player_name:
            title_matches = _TITLE_RE.findall(chunk)
            for t in title_matches:
                t = _clean_text(t)
                if t and t.lower() != player_slug.replace("-", " ").lower():
                    player_name = t
                    break

        if not player_name:
            continue

        seen.add(player_id)
        players.append(
            {
                "player_id": player_id,
                "player_slug": player_slug,
                "player_name": player_name,
            }
        )

    return players


def parse_players_from_stats_page(html: str) -> list[dict]:
    dom_players = _parse_players_dom(html)
    if dom_players:
        return dom_players
    return _parse_players_regex(html)


def _parse_date_to_iso(text: str | None) -> str | None:
    if not text:
        return None

    value = _clean_text(text)
    if not value:
        return None

    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def _extract_profile_rows(soup: BeautifulSoup) -> list:
    selectors = [
        "div.p_lg div.d_flex.flex-wrap-wrap.mt_md > div.d_flex.ai_center.gap_xs",
        "div.p_lg div.d_flex.flex-wrap-wrap.mt_md > div",
        "div.d_flex.flex-wrap-wrap.mt_md > div.d_flex.ai_center.gap_xs",
    ]

    for selector in selectors:
        rows = soup.select(selector)
        if rows:
            return rows

    return []


def parse_player_profile(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")


    canonical_slug = None

    canon = soup.select_one('link[rel="canonical"]')
    if canon:
        href = (canon.get("href") or "").strip()
        m = _PLAYER_RE.search(href)
        if m:
            canonical_slug = m.group(1)

    rows = _extract_profile_rows(soup)

    for row in rows:
        row_text = _clean_text(row.get_text(" ", strip=True))
        if not row_text:
            continue




