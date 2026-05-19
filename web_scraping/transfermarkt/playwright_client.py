from __future__ import annotations

import random
import time
from typing import Optional

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


class PlaywrightClient:
    """Browser automation client using Playwright for scraping JavaScript-heavy websites."""

    DEFAULT_NAV_TIMEOUT_MS = 30000
    DEFAULT_SELECTOR_TIMEOUT_MS = 12000
    DEFAULT_NETWORKIDLE_TIMEOUT_MS = 5000
    DEFAULT_MAX_ATTEMPTS = 4

    def __init__(
        self,
        *,
        browser_name: str = "chromium",
        headless: bool = True,
        slow_mo_ms: int = 0,
        nav_timeout_ms: int = DEFAULT_NAV_TIMEOUT_MS,
        selector_timeout_ms: int = DEFAULT_SELECTOR_TIMEOUT_MS,
        networkidle_timeout_ms: int = DEFAULT_NETWORKIDLE_TIMEOUT_MS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        locale: str = "de-CH",
        timezone_id: str = "Europe/Zurich",
        user_agent: str = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        channel: Optional[str] = None,
    ) -> None:
        """Initialize Playwright browser client with configuration."""
        self.browser_name = browser_name
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.nav_timeout_ms = nav_timeout_ms
        self.selector_timeout_ms = selector_timeout_ms
        self.networkidle_timeout_ms = networkidle_timeout_ms
        self.max_attempts = max_attempts
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_agent = user_agent
        self.channel = channel

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def _ensure_context(self) -> None:
        """Ensure browser context is initialized."""
        if self._context is not None:
            return

        self._playwright = sync_playwright().start()

        if self.browser_name not in {"chromium", "firefox", "webkit"}:
            raise ValueError(
                f"Unsupported browser_name={self.browser_name!r}. "
                "Use 'chromium', 'firefox', or 'webkit'."
            )

        launcher = getattr(self._playwright, self.browser_name)

        launch_kwargs = {
            "headless": self.headless,
            "slow_mo": self.slow_mo_ms,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        if self.channel:
            launch_kwargs["channel"] = self.channel

        self._browser = launcher.launch(**launch_kwargs)

        self._context = self._browser.new_context(
            locale=self.locale,
            timezone_id=self.timezone_id,
            user_agent=self.user_agent,
            viewport={"width": 1440, "height": 900},
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
            },
        )
        self._context.set_default_timeout(self.selector_timeout_ms)
        self._context.set_default_navigation_timeout(self.nav_timeout_ms)

    @staticmethod
    def _looks_blocked(html: str) -> bool:
        """Check if HTML indicates the page was blocked or requires verification."""
        html_lower = html.lower()

        blocked_indicators = [
            "captcha",
            "verify you are human",
            "attention required",
            "cloudfront",
            "request blocked",
            "waf",
            "access denied",
            "bot",
        ]

        return any(indicator in html_lower for indicator in blocked_indicators)

    def get(self, url: str, *, required_selector: str | None = None) -> str:
        """Fetch URL and return HTML content with automatic retry on failure."""
        last_exc: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            page: Page | None = None

            try:
                self._ensure_context()
                assert self._context is not None

                page = self._context.new_page()

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.nav_timeout_ms,
                )

                status = response.status if response is not None else None
                if status == 202:
                    raise RuntimeError(f"retryable status 202: {url}")

                try:
                    page.wait_for_load_state(
                        "networkidle",
                        timeout=self.networkidle_timeout_ms,
                    )
                except PlaywrightTimeoutError:
                    pass

                if required_selector:
                    page.wait_for_selector(
                        required_selector,
                        state="attached",
                        timeout=self.selector_timeout_ms,
                    )

                html = page.content()

                if self._looks_blocked(html):
                    raise RuntimeError(f"blocked/challenge HTML detected: {url}")

                if required_selector == "table" and "<table" not in html.lower():
                    raise RuntimeError(f"required table not found in HTML: {url}")

                return html

            except Exception as error:
                last_exc = error

                if attempt >= self.max_attempts:
                    raise

                sleep_seconds = min(20.0, (2 ** (attempt - 1)) * 1.5) + random.random()
                print(
                    f"[WARN] playwright retry {attempt}/{self.max_attempts}: "
                    f"{url} -> {error}"
                )
                time.sleep(sleep_seconds)

            finally:
                if page is not None:
                    try:
                        page.close()
                    except Exception:
                        pass

        if last_exc is not None:
            raise last_exc

        raise RuntimeError("Playwright request failed without exception")

    def close(self) -> None:
        """Close browser, context and playwright resources."""
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

