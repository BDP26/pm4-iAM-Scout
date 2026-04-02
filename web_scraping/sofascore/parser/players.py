from __future__ import annotations

from datetime import datetime
import re

from bs4 import BeautifulSoup


class SofaScorePlayersParser:
    PLAYER_RE = re.compile(r'/football/player/([^/"\'?#]+)/(\d+)')
    TITLE_RE = re.compile(r'title="([^"]+)"')

    @staticmethod
    def _clean_text(x: str | None) -> str | None:
        if x is None:
            return None
        x = re.sub(r"\s+", " ", x).strip()
        return x or None

    @staticmethod
    def _slug_to_name(slug: str | None) -> str | None:
        if not slug:
            return None

        value = slug.replace("-", " ").strip()
        if not value:
            return None

        return value.title()

    def _extract_player_name_from_anchor(self, a, player_slug: str) -> str | None:
        text = self._clean_text(a.get_text(" ", strip=True))
        if text:
            return text

        for attr in ("title", "aria-label"):
            value = self._clean_text(a.get(attr))
            if value:
                return value

        return self._slug_to_name(player_slug)

    def _parse_players_dom(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")

        players: list[dict] = []
        seen: set[str] = set()

        candidate_links = soup.select('a[href*="/football/player/"]')

        for a in candidate_links:
            href = (a.get("href") or "").strip()
            pm = self.PLAYER_RE.search(href)
            if not pm:
                continue

            player_slug, player_id = pm.group(1), pm.group(2)
            if player_id in seen:
                continue

            player_name = self._extract_player_name_from_anchor(a, player_slug)
            if not player_name:
                continue

            seen.add(player_id)
            players.append(
                {
                    "id": player_id,
                    "slug": player_slug,
                    "name": player_name,
                }
            )

        return players

    def _parse_players_regex(self, html: str) -> list[dict]:
        players: list[dict] = []
        seen: set[str] = set()

        for pm in self.PLAYER_RE.finditer(html):
            player_slug, player_id = pm.group(1), pm.group(2)
            if player_id in seen:
                continue

            start = max(0, pm.start() - 1200)
            end = min(len(html), pm.end() + 1200)
            chunk = html[start:end]

            player_name = None

            anchor_match = re.search(
                rf'href="[^"]*/football/player/{re.escape(player_slug)}/{player_id}"[^>]*>([^<]+)</a>',
                chunk,
            )
            if anchor_match:
                player_name = self._clean_text(anchor_match.group(1))

            if not player_name:
                attr_match = re.search(
                    rf'href="[^"]*/football/player/{re.escape(player_slug)}/{player_id}"[^>]*(?:title|aria-label)="([^"]+)"',
                    chunk,
                )
                if attr_match:
                    player_name = self._clean_text(attr_match.group(1))

            if not player_name:
                title_matches = self.TITLE_RE.findall(chunk)
                for t in title_matches:
                    t = self._clean_text(t)
                    if t and t.lower() != player_slug.replace("-", " ").lower():
                        player_name = t
                        break

            if not player_name:
                player_name = self._slug_to_name(player_slug)

            if not player_name:
                continue

            seen.add(player_id)
            players.append(
                {
                    "id": player_id,
                    "slug": player_slug,
                    "name": player_name,
                }
            )

        return players

    def parse_players_from_stats_page(self, html: str) -> list[dict]:
        dom_players = self._parse_players_dom(html)
        if dom_players:
            return dom_players
        return self._parse_players_regex(html)

    @staticmethod
    def _parse_date_to_iso(text: str | None) -> str | None:
        if not text:
            return None

        value = SofaScorePlayersParser._clean_text(text)
        if not value:
            return None

        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue

        return None

    def _extract_profile_rows(self, soup: BeautifulSoup) -> list:
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

    def parse_player_profile(self, html: str) -> dict:
        soup = BeautifulSoup(html, "lxml")

        canonical_slug = None
        canon = soup.select_one('link[rel="canonical"]')
        if canon:
            href = (canon.get("href") or "").strip()
            m = self.PLAYER_RE.search(href)
            if m:
                canonical_slug = m.group(1)

        result: dict = {}
        if canonical_slug:
            result["canonical_slug"] = canonical_slug

        return result