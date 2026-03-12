from __future__ import annotations

import re
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from web_scraping.config import (
    SOFASCORE_PLAYER_PROFILE_URL,
    SOFASCORE_PLAYER_URL,
    SLEEP_SECONDS,
)


class SofaScoreClient:
    def __init__(self, sleep_seconds: float = SLEEP_SECONDS) -> None:
        self.sleep_seconds = sleep_seconds
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        self.accept_language = "en-US,en;q=0.9,de;q=0.8"

        self._playwright = None
        self._browser = None
        self._context = None

    def _ensure_browser(self) -> None:
        if self._context is not None:
            return

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = self._browser.new_context(
            user_agent=self.user_agent,
            locale="en-US",
            viewport={"width": 1440, "height": 2200},
            extra_http_headers={
                "Accept-Language": self.accept_language,
            },
        )

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None

        if self._browser is not None:
            self._browser.close()
            self._browser = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "SofaScoreClient":
        self._ensure_browser()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _new_page(self):
        self._ensure_browser()
        return self._context.new_page()

    @staticmethod
    def _extract_player_ids(html: str) -> tuple[str, ...]:
        ids = re.findall(r'/football/player/[^/"\'?#]+/(\d+)', html)
        return tuple(sorted(set(ids)))

    def _wait_for_stats_ready(self, page) -> None:
        page.wait_for_selector('a[href*="/football/player/"]', timeout=30000)
        page.wait_for_timeout(1500)

    def _get_paginator_container(self, page):
        """
        Erwarteter DOM laut Inspect:
        <div class="d_flex ai_center jc_center py_lg">
            <button>prev</button>
            <div>
                <button>1</button>
                <button>2</button>
                <span>...</span>
                <button>19</button>
            </div>
            <button><svg ...></svg></button>
        </div>
        """
        loc = page.locator("div.d_flex.ai_center.jc_center.py_lg")
        if loc.count() > 0:
            return loc.first

        # Fallback, falls Klassen leicht variieren
        fallback = page.locator(
            "xpath=//div[./button and ./div and count(./button)=2]"
        )
        if fallback.count() > 0:
            return fallback.first

        return None

    def _get_total_pages(self, page) -> int:
        container = self._get_paginator_container(page)
        if container is None:
            return 1

        numeric_buttons = container.locator("xpath=./div//button")
        texts = numeric_buttons.all_inner_texts()

        nums: list[int] = []
        for t in texts:
            t = t.strip()
            if t.isdigit():
                nums.append(int(t))

        return max(nums) if nums else 1

    def _click_paginator_next(self, page) -> bool:
        container = self._get_paginator_container(page)
        if container is None:
            return False

        side_buttons = container.locator("xpath=./button")
        if side_buttons.count() < 2:
            return False

        next_button = side_buttons.nth(1)

        try:
            if next_button.is_disabled():
                return False
        except Exception:
            pass

        try:
            aria_disabled = next_button.get_attribute("aria-disabled")
            if aria_disabled == "true":
                return False
        except Exception:
            pass

        try:
            next_button.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            next_button.click(timeout=10000)
            return True
        except Exception:
            pass

        # harter Fallback: DOM-click auf dem Button
        try:
            handle = next_button.element_handle()
            if handle is None:
                return False
            page.evaluate("(el) => el.click()", handle)
            return True
        except Exception:
            return False

    def _wait_until_player_ids_change(self, page, previous_ids: tuple[str, ...]) -> bool:
        for _ in range(20):
            page.wait_for_timeout(700)
            html = page.content()
            current_ids = self._extract_player_ids(html)
            if current_ids and current_ids != previous_ids:
                return True
        return False

    def get_stats_pages(self, season_id: int | str, max_pages: int = 60) -> list[str]:
        url = SOFASCORE_PLAYER_URL.format(season_id=season_id)
        page = self._new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self._wait_for_stats_ready(page)

            total_pages = min(self._get_total_pages(page), max_pages)
            print(f"[DEBUG] Stats paginator total pages: {total_pages}")

            pages: list[str] = []
            seen_signatures: set[tuple[str, ...]] = set()

            html = page.content()
            ids = self._extract_player_ids(html)

            if ids:
                pages.append(html)
                seen_signatures.add(ids)
                print(f"[DEBUG] Collected stats page 1 with {len(ids)} player links")

            current_page = 1

            while current_page < total_pages:
                previous_ids = self._extract_player_ids(page.content())

                clicked = self._click_paginator_next(page)
                if not clicked:
                    print(f"[WARN] Could not click paginator next after page {current_page}")
                    break

                changed = self._wait_until_player_ids_change(page, previous_ids)
                if not changed:
                    print(f"[WARN] Stats page after {current_page} did not change")
                    break

                page.wait_for_timeout(1000)

                html = page.content()
                ids = self._extract_player_ids(html)

                if not ids:
                    print(f"[WARN] No player ids found after page {current_page}")
                    break

                if ids in seen_signatures:
                    print(f"[WARN] Duplicate player set after page {current_page}")
                    break

                current_page += 1
                seen_signatures.add(ids)
                pages.append(html)
                print(f"[DEBUG] Collected stats page {current_page} with {len(ids)} player links")

            time.sleep(self.sleep_seconds)
            return pages

        finally:
            page.close()

    def get_player_profile(self, player_slug: str, player_id: int | str) -> str:
        url = SOFASCORE_PLAYER_PROFILE_URL.format(
            player_slug=player_slug,
            player_id=player_id,
        )

        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            try:
                page.wait_for_selector("h1", timeout=15000)
            except PlaywrightTimeoutError:
                page.wait_for_timeout(3000)

            page.wait_for_timeout(1500)
            html = page.content()
            time.sleep(self.sleep_seconds)
            return html

        finally:
            page.close()