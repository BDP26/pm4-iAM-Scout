from __future__ import annotations

from datetime import date, datetime
import re

from bs4 import BeautifulSoup, Tag


class SofaScorePlayerStatsParser:
    DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{2,4}\b")
    RATING_RE = re.compile(r"\b(?:[3-9](?:\.\d)?|10(?:\.0)?)\b")

    @staticmethod
    def _clean_text(x: str | None) -> str | None:
        if x is None:
            return None
        x = re.sub(r"\s+", " ", x).strip()
        return x or None

    @staticmethod
    def _parse_ui_date(text: str | None) -> date | None:
        if not text:
            return None

        value = text.strip()

        for fmt in ("%d/%m/%y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def _parse_rating_value(text: str | None) -> float | None:
        if not text:
            return None

        value = text.strip().replace(",", ".")
        try:
            rating = float(value)
        except ValueError:
            return None

        if 0.0 <= rating <= 10.0:
            return rating

        return None

    def _extract_date(self, row: Tag) -> date | None:
        # Screenshot: <div title="FT"> ... <bdi>15/03/26</bdi>
        for bdi in row.select("bdi"):
            text = self._clean_text(bdi.get_text(" ", strip=True))
            if not text:
                continue

            match = self.DATE_RE.search(text)
            if not match:
                continue

            parsed = self._parse_ui_date(match.group(0))
            if parsed:
                return parsed

        text = self._clean_text(row.get_text(" ", strip=True))
        if text:
            match = self.DATE_RE.search(text)
            if match:
                return self._parse_ui_date(match.group(0))

        return None

    def _extract_rating(self, row: Tag) -> float | None:
        # Screenshot: <span role="meter" aria-valuenow="6.8"> ... data-rating="6.8" ... <span>6.8</span>
        meter = row.select_one('span[role="meter"][aria-valuenow]')
        if meter is not None:
            rating = self._parse_rating_value(meter.get("aria-valuenow"))
            if rating is not None:
                return rating

        rated = row.select_one("[data-rating]")
        if rated is not None:
            rating = self._parse_rating_value(rated.get("data-rating"))
            if rating is not None:
                return rating

        for span in row.select("span"):
            text = self._clean_text(span.get_text(" ", strip=True))
            rating = self._parse_rating_value(text)
            if rating is not None:
                return rating

        text = self._clean_text(row.get_text(" ", strip=True))
        if text:
            match = self.RATING_RE.search(text)
            if match:
                return self._parse_rating_value(match.group(0))

        return None

    def parse_player_matches(
        self,
        html: str,
        player_name: str,
        min_date: str = "2024-01-01",
    ) -> list[dict]:
        cutoff = datetime.fromisoformat(min_date).date()
        soup = BeautifulSoup(html, "lxml")

        rows: list[dict] = []
        seen: set[str] = set()

        for row in soup.select("a[data-id]"):
            match_id = (row.get("data-id") or "").strip()

            match_date = self._extract_date(row)
            if match_date is None or match_date < cutoff:
                continue

            rating = self._extract_rating(row)
            if rating is None:
                continue

            key = match_id or f"{player_name}|{match_date.isoformat()}|{rating}"
            if key in seen:
                continue

            seen.add(key)
            rows.append(
                {
                    "name": player_name,
                    "datum": match_date.isoformat(),
                    "rating": rating,
                }
            )

        rows.sort(key=lambda x: (x["datum"], x["name"]))
        return rows