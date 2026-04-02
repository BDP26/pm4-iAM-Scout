from __future__ import annotations

import re
import time
from datetime import date, datetime

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class SofaScoreClient:
    DEFAULT_SLEEP_SECONDS = 0.01
    DEFAULT_PLAYER_PROFILE_URL = (
        "https://www.sofascore.com/football/player/{player_slug}/{player_id}"
    )

    def __init__(
        self,
        sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
        stats_url_template: str | None = None,
        player_profile_url_template: str = DEFAULT_PLAYER_PROFILE_URL,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.stats_url_template = stats_url_template
        self.player_profile_url_template = player_profile_url_template

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
        page = self._context.new_page()

        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"image", "font", "media"}
            else route.continue_(),
        )

        return page

    def _resolve_stats_url(self, season_id: int | str) -> str:
        value = str(season_id).strip()

        if value.startswith("http://") or value.startswith("https://"):
            return value

        if not self.stats_url_template:
            raise ValueError(
                "stats_url_template ist nicht gesetzt. "
                "Entweder eine vollständige URL an get_stats_pages(...) übergeben "
                "oder SofaScoreClient(stats_url_template='...') verwenden."
            )

        return self.stats_url_template.format(season_id=value)

    def _build_player_profile_url(self, player_slug: str, player_id: int | str) -> str:
        return self.player_profile_url_template.format(
            player_slug=player_slug,
            player_id=player_id,
        )

    @staticmethod
    def _extract_player_ids(html: str) -> tuple[str, ...]:
        ids = re.findall(r'/football/player/[^/"\'?#]+/(\d+)', html)
        return tuple(sorted(set(ids)))

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

    def _wait_for_stats_ready(self, page) -> None:
        page.wait_for_selector('a[href*="/football/player/"]', timeout=12000)
        page.wait_for_timeout(500)

    def _wait_for_player_profile_ready(self, page) -> None:
        try:
            page.wait_for_selector("h1", timeout=8000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(800)

        page.wait_for_timeout(200)

    def _wait_for_player_matches_ready(self, page) -> None:
        self._wait_for_player_profile_ready(page)

        selectors = [
            'a[data-id]',
            'text=All competitions',
            'button:has-text("All competitions")',
            '[role="button"]:has-text("All competitions")',
        ]

        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=2500)
                break
            except Exception:
                continue

        page.wait_for_timeout(150)

    def _get_paginator_container(self, page):
        containers = [
            page.locator("div.d_flex.ai_center.jc_center.py_lg"),
            page.locator("xpath=//div[contains(@class, 'jc_center') and .//button]"),
            page.locator("xpath=//div[.//button and count(.//button)>=2]"),
            page.locator("xpath=//nav[.//button and count(.//button)>=2]"),
        ]

        for group in containers:
            try:
                count = min(group.count(), 20)
            except Exception:
                count = 0

            for i in range(count):
                container = group.nth(i)

                try:
                    if not container.is_visible():
                        continue
                except Exception:
                    continue

                try:
                    button_count = container.locator("button").count()
                except Exception:
                    continue

                if button_count >= 2:
                    return container

        return None

    def _get_total_pages(self, page) -> int:
        container = self._get_paginator_container(page)
        if container is None:
            return 1

        texts: list[str] = []

        locators = [
            container.locator("button"),
            container.locator("div"),
            container.locator("span"),
        ]

        for locator in locators:
            try:
                texts.extend(locator.all_inner_texts())
            except Exception:
                continue

        nums: list[int] = []
        for text in texts:
            for raw in re.findall(r"\b\d+\b", text):
                try:
                    nums.append(int(raw))
                except ValueError:
                    continue

        return max(nums) if nums else 1

    def _click_paginator_next(self, page) -> bool:
        container = self._get_paginator_container(page)
        if container is None:
            return False

        candidate_groups = [
            container.locator("xpath=./button"),
            container.locator("button"),
        ]

        for group in candidate_groups:
            try:
                count = group.count()
            except Exception:
                count = 0

            for idx in range(count - 1, -1, -1):
                button = group.nth(idx)

                try:
                    if not button.is_visible():
                        continue
                except Exception:
                    continue

                try:
                    text = (button.inner_text() or "").strip()
                    if text.isdigit():
                        continue
                except Exception:
                    pass

                try:
                    disabled_attr = button.get_attribute("disabled")
                    aria_disabled = button.get_attribute("aria-disabled")
                    if disabled_attr is not None or aria_disabled == "true":
                        continue
                except Exception:
                    pass

                try:
                    if button.is_disabled():
                        continue
                except Exception:
                    pass

                try:
                    button.scroll_into_view_if_needed()
                except Exception:
                    pass

                try:
                    button.click(timeout=2500)
                    page.wait_for_timeout(200)
                    return True
                except Exception:
                    try:
                        handle = button.element_handle()
                        if handle is not None:
                            page.evaluate("(el) => el.click()", handle)
                            page.wait_for_timeout(200)
                            return True
                    except Exception:
                        continue

        return False

    def _wait_until_player_ids_change(
        self,
        page,
        previous_ids: tuple[str, ...],
        max_tries: int = 20,
    ) -> bool:
        for _ in range(max_tries):
            page.wait_for_timeout(150)
            html = page.content()
            current_ids = self._extract_player_ids(html)
            if current_ids and current_ids != previous_ids:
                return True
        return False

    def _open_matches_tab(self, page) -> None:
        candidates = [
            page.get_by_role("tab", name=re.compile(r"^Matches$", re.I)),
            page.locator('a:has-text("Matches")'),
            page.locator('button:has-text("Matches")'),
            page.locator('text="Matches"'),
        ]

        for group in candidates:
            try:
                count = min(group.count(), 10)
            except Exception:
                count = 0

            for i in range(count):
                locator = group.nth(i)
                try:
                    if locator.is_visible():
                        locator.scroll_into_view_if_needed()
                        try:
                            locator.click(timeout=2500)
                        except Exception:
                            handle = locator.element_handle()
                            if handle is not None:
                                page.evaluate("(el) => el.click()", handle)
                        page.wait_for_timeout(200)
                        return
                except Exception:
                    continue

    def _is_competition_dropdown_open(self, page) -> bool:
        try:
            return page.locator('li[role="option"]').count() > 0
        except Exception:
            return False

    def _click_first_visible(self, page, locator_group) -> bool:
        try:
            count = min(locator_group.count(), 10)
        except Exception:
            return False

        for i in range(count):
            locator = locator_group.nth(i)
            try:
                if not locator.is_visible():
                    continue

                locator.scroll_into_view_if_needed()

                try:
                    locator.click(timeout=2500)
                    return True
                except Exception:
                    handle = locator.element_handle()
                    if handle is not None:
                        page.evaluate("(el) => el.click()", handle)
                        return True
            except Exception:
                continue

        return False

    def _open_competition_dropdown(self, page) -> None:
        if self._is_competition_dropdown_open(page):
            return

        candidates = [
            page.get_by_text("All competitions", exact=True),
            page.locator('text="All competitions"'),
            page.locator("xpath=//*[normalize-space(text())='All competitions']"),
            page.locator("xpath=//*[contains(normalize-space(.), 'All competitions')]"),
        ]

        for group in candidates:
            clicked = self._click_first_visible(page, group)
            if not clicked:
                continue

            for _ in range(8):
                page.wait_for_timeout(100)
                if self._is_competition_dropdown_open(page):
                    return

        raise RuntimeError("Competition dropdown konnte nicht geöffnet werden")

    def _select_competition(self, page, competition: str) -> None:
        self._open_competition_dropdown(page)

        candidates = [
            page.locator('li[role="option"]').filter(has_text=competition),
            page.get_by_role("option", name=competition),
            page.get_by_text(competition, exact=True),
        ]

        for group in candidates:
            try:
                count = min(group.count(), 10)
            except Exception:
                count = 0

            for i in range(count):
                locator = group.nth(i)
                try:
                    if not locator.is_visible():
                        continue

                    locator.scroll_into_view_if_needed()

                    try:
                        locator.click(timeout=2500)
                    except Exception:
                        handle = locator.element_handle()
                        if handle is not None:
                            page.evaluate("(el) => el.click()", handle)

                    page.wait_for_timeout(200)
                    return
                except Exception:
                    continue

        raise RuntimeError(f"Competition '{competition}' nicht im Dropdown gefunden")

    def _extract_oldest_visible_match_date(self, html: str) -> date | None:
        candidates = re.findall(r"\b\d{2}/\d{2}/\d{2,4}\b", html)

        parsed_dates: list[date] = []
        for raw in candidates:
            parsed = self._parse_ui_date(raw)
            if parsed is not None:
                parsed_dates.append(parsed)

        if not parsed_dates:
            return None

        return min(parsed_dates)

    def _get_match_history_paginator(self, page):
        containers = [
            page.locator("div.d_flex.ai_center.jc_space-between.gap_sm.p_md"),
            page.locator("xpath=//div[count(./button)=2]"),
        ]

        for group in containers:
            try:
                count = group.count()
            except Exception:
                count = 0

            for i in range(count):
                container = group.nth(i)
                try:
                    buttons = container.locator("button")
                    if buttons.count() == 2 and container.is_visible():
                        return container
                except Exception:
                    continue

        return None

    def _extract_match_row_ids(self, page) -> tuple[str, ...]:
        try:
            loc = page.locator("a[data-id]")
            count = loc.count()
        except Exception:
            return tuple()

        ids: list[str] = []
        for i in range(count):
            try:
                value = (loc.nth(i).get_attribute("data-id") or "").strip()
                if value:
                    ids.append(value)
            except Exception:
                continue

        return tuple(ids)

    def _click_match_history_next(self, page) -> bool:
        container = self._get_match_history_paginator(page)
        if container is None:
            return False

        buttons = container.locator("button")
        if buttons.count() < 2:
            return False

        for idx in [0, 1]:
            button = buttons.nth(idx)

            try:
                if not button.is_visible():
                    continue
            except Exception:
                continue

            try:
                disabled_attr = button.get_attribute("disabled")
                aria_disabled = button.get_attribute("aria-disabled")
                if disabled_attr is not None or aria_disabled == "true":
                    continue
            except Exception:
                pass

            try:
                if button.is_disabled():
                    continue
            except Exception:
                pass

            try:
                button.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                button.click(timeout=2500)
                page.wait_for_timeout(200)
                return True
            except Exception:
                try:
                    handle = button.element_handle()
                    if handle is not None:
                        page.evaluate("(el) => el.click()", handle)
                        page.wait_for_timeout(200)
                        return True
                except Exception:
                    continue

        return False

    def _wait_until_match_page_changes(
        self,
        page,
        previous_ids: tuple[str, ...],
        max_tries: int = 12,
    ) -> bool:
        for _ in range(max_tries):
            page.wait_for_timeout(100)
            current_ids = self._extract_match_row_ids(page)
            if current_ids and current_ids != previous_ids:
                return True
        return False

    def _collect_match_history_pages(
        self,
        page,
        min_date: str,
        max_rounds: int = 80,
    ) -> list[str]:
        cutoff = datetime.fromisoformat(min_date).date()
        collected_html: list[str] = []
        seen_signatures: set[tuple[str, ...]] = set()

        for round_no in range(1, max_rounds + 1):
            current_html = page.content()
            current_ids = self._extract_match_row_ids(page)

            if current_ids and current_ids not in seen_signatures:
                collected_html.append(current_html)
                seen_signatures.add(current_ids)
                print(
                    f"[DEBUG] Collected match page {round_no} "
                    f"with {len(current_ids)} matches"
                )

            oldest = self._extract_oldest_visible_match_date(current_html)
            if oldest is not None and oldest <= cutoff:
                print(f"[DEBUG] Match history reached cutoff {cutoff} at round {round_no}")
                break

            previous_ids = current_ids
            clicked = self._click_match_history_next(page)

            if not clicked:
                print(
                    f"[DEBUG] No enabled match-history paginator button found "
                    f"at round {round_no}"
                )
                break

            changed = self._wait_until_match_page_changes(page, previous_ids)
            if not changed:
                print(
                    f"[DEBUG] Match page did not change after paginator click "
                    f"at round {round_no}"
                )
                break

        return collected_html

    def get_stats_pages(self, season_id: int | str, max_pages: int = 60) -> list[str]:
        url = self._resolve_stats_url(season_id)
        page = self._new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._wait_for_stats_ready(page)

            total_pages_estimate = min(self._get_total_pages(page), max_pages)
            print(f"[DEBUG] Stats paginator total pages: {total_pages_estimate}")

            pages: list[str] = []
            seen_signatures: set[tuple[str, ...]] = set()

            html = page.content()
            ids = self._extract_player_ids(html)

            if not ids:
                print("[WARN] No player ids found on initial stats page")
                time.sleep(self.sleep_seconds)
                return pages

            pages.append(html)
            seen_signatures.add(ids)
            print(f"[DEBUG] Collected stats page 1 with {len(ids)} player links")

            current_page = 1

            while current_page < max_pages:
                previous_ids = ids

                clicked = self._click_paginator_next(page)
                if not clicked:
                    break

                changed = self._wait_until_player_ids_change(page, previous_ids)
                if not changed:
                    print(f"[WARN] Stats page after {current_page} did not change")
                    break

                page.wait_for_timeout(200)

                html = page.content()
                ids = self._extract_player_ids(html)

                if not ids:
                    print(f"[WARN] No player ids found after page {current_page}")
                    break

                if ids in seen_signatures:
                    break

                current_page += 1
                seen_signatures.add(ids)
                pages.append(html)
                print(
                    f"[DEBUG] Collected stats page {current_page} "
                    f"with {len(ids)} player links"
                )

            time.sleep(self.sleep_seconds)
            return pages

        finally:
            page.close()

    def get_player_profile(self, player_slug: str, player_id: int | str) -> str:
        url = self._build_player_profile_url(
            player_slug=player_slug,
            player_id=player_id,
        )

        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._wait_for_player_profile_ready(page)

            html = page.content()
            time.sleep(self.sleep_seconds)
            return html

        finally:
            page.close()

    def get_player_match_history_pages(
        self,
        player_slug: str,
        player_id: int | str,
        competition: str = "Swiss Super League",
        min_date: str = "2024-01-01",
    ) -> list[str]:
        url = self._build_player_profile_url(
            player_slug=player_slug,
            player_id=player_id,
        )

        page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._wait_for_player_matches_ready(page)

            self._open_matches_tab(page)
            self._select_competition(page, competition)

            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(150)

            pages = self._collect_match_history_pages(page, min_date=min_date)
            time.sleep(self.sleep_seconds)
            return pages

        finally:
            page.close()

    def get_player_match_history_html(
        self,
        player_slug: str,
        player_id: int | str,
        competition: str = "Swiss Super League",
        min_date: str = "2024-01-01",
    ) -> str:
        pages = self.get_player_match_history_pages(
            player_slug=player_slug,
            player_id=player_id,
            competition=competition,
            min_date=min_date,
        )
        return "\n<!-- PAGE BREAK -->\n".join(pages)