from __future__ import annotations

import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    DEFAULT_CONNECT_TIMEOUT = 10
    DEFAULT_READ_TIMEOUT = 60

    DEFAULT_TOTAL_RETRIES = 5
    DEFAULT_BACKOFF_FACTOR = 1.0

    STATUS_FORCELIST = (429, 500, 502, 503, 504)
    RETRYABLE_EMPTY_STATUSES = (202, 204)

    def __init__(
        self,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        total_retries: int = DEFAULT_TOTAL_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = STATUS_FORCELIST,
        max_attempts: int = 5,
    ):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.timeout = (connect_timeout, read_timeout)

        self.total_retries = total_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist
        self.max_attempts = max_attempts

        self.session = self._make_session()

    def _make_session(self) -> requests.Session:
        session = requests.Session()

        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
            }
        )

        retry = Retry(
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
            max_retries=retry,
            pool_connections=20,
            pool_maxsize=20,
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    @staticmethod
    def _retry_after_to_seconds(value: str | None) -> int | None:
        if not value:
            return None
        value = value.strip()
        if value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _compute_sleep(attempt: int, retry_after: int | None = None) -> float:
        if retry_after is not None:
            return float(min(90, max(1, retry_after)))

        base = min(30.0, (2 ** (attempt - 1)) * 1.5)
        jitter = random.uniform(0.3, 1.3)
        return base + jitter

    def get(self, url: str) -> str:
        last_exc: Exception | None = None
        last_reason: str | None = None

        for attempt in range(1, self.max_attempts + 1):
            response: requests.Response | None = None

            try:
                response = self.session.get(url, timeout=self.timeout)

                status_code = response.status_code
                retry_after = self._retry_after_to_seconds(
                    response.headers.get("Retry-After")
                )

                if status_code == 429:
                    last_reason = f"status {status_code}"
                    if attempt >= self.max_attempts:
                        response.raise_for_status()
                    time.sleep(self._compute_sleep(attempt, retry_after))
                    continue

                if status_code in self.RETRYABLE_EMPTY_STATUSES:
                    last_reason = f"status {status_code}"
                    if attempt >= self.max_attempts:
                        raise RuntimeError(
                            f"request returned retryable status {status_code} "
                            f"after {self.max_attempts} attempts: {url}"
                        )
                    time.sleep(self._compute_sleep(attempt, retry_after))
                    continue

                response.raise_for_status()

                text = response.text or ""
                if not text.strip():
                    last_reason = "empty body"
                    if attempt >= self.max_attempts:
                        raise RuntimeError(
                            f"request returned empty body after "
                            f"{self.max_attempts} attempts: {url}"
                        )
                    time.sleep(self._compute_sleep(attempt, retry_after))
                    continue

                return text

            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    raise
                time.sleep(self._compute_sleep(attempt))

            finally:
                if response is not None:
                    response.close()

        if last_exc is not None:
            raise last_exc

        raise RuntimeError(
            f"request failed after {self.max_attempts} attempts: {url}. "
            f"Last reason: {last_reason or 'unknown'}"
        )