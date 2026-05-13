from __future__ import annotations

import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """HTTP client with retry logic and rate limiting support."""

    DEFAULT_CONNECT_TIMEOUT = 10
    DEFAULT_READ_TIMEOUT = 60
    DEFAULT_TOTAL_RETRIES = 5
    DEFAULT_BACKOFF_FACTOR = 1.0
    STATUS_FORCELIST = (202, 429, 500, 502, 503, 504)

    def __init__(
        self,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        total_retries: int = DEFAULT_TOTAL_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = STATUS_FORCELIST,
        max_attempts: int = 5,
    ):
        """Initialize HTTP client with connection and retry settings."""
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.timeout = (connect_timeout, read_timeout)
        self.total_retries = total_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist
        self.max_attempts = max_attempts
        self.session = self._make_session()

    def _make_session(self) -> requests.Session:
        """Create and configure a requests session with retry strategy."""
        session = requests.Session()

        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
            }
        )

        retry_strategy = Retry(
            total=self.total_retries,
            connect=self.total_retries,
            read=self.total_retries,
            status=self.total_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods={"GET"},
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def get(self, url: str) -> str:
        """Fetch URL content with automatic retry on failure."""
        last_exc: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)

                if response.status_code == 202:
                    raise requests.exceptions.HTTPError(
                        f"retryable status 202 on attempt {attempt}: {url}"
                    )

                if response.status_code == 429:
                    retry_after = (response.headers.get("Retry-After") or "").strip()
                    wait_seconds = int(retry_after) if retry_after.isdigit() else min(60, 5 * attempt)
                    time.sleep(wait_seconds)
                    raise requests.exceptions.HTTPError(
                        f"retryable status 429 on attempt {attempt}: {url}"
                    )

                response.raise_for_status()
                return response.text

            except requests.exceptions.RequestException as error:
                last_exc = error

                if attempt >= self.max_attempts:
                    raise

                sleep_seconds = min(30.0, (2 ** (attempt - 1)) * 1.5) + random.random()
                print(f"[WARN] request retry {attempt}/{self.max_attempts}: {url} -> {error}")
                time.sleep(sleep_seconds)

        if last_exc:
            raise last_exc

        raise RuntimeError("request failed without exception")