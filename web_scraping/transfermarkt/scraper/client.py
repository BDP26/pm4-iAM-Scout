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

    def __init__(
        self,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        total_retries: int = DEFAULT_TOTAL_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        status_forcelist: tuple[int, ...] = STATUS_FORCELIST,
        max_attempts: int = 2,
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

        s = requests.Session()

        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
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

        s.mount("https://", adapter)
        s.mount("http://", adapter)

        return s

    def get(self, url: str) -> str:

        last_exc: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):

            try:
                r = self.session.get(url, timeout=self.timeout)

                if r.status_code == 429:
                    ra = (r.headers.get("Retry-After") or "").strip()
                    wait_s = int(ra) if ra.isdigit() else min(60, 5 * attempt)
                    time.sleep(wait_s)

                r.raise_for_status()
                return r.text

            except requests.exceptions.RequestException as e:

                last_exc = e

                if attempt >= self.max_attempts:
                    raise

                sleep_s = min(30.0, (2 ** (attempt - 1)) * 1.5) + random.random()
                time.sleep(sleep_s)

        if last_exc:
            raise last_exc

        raise RuntimeError("request failed without exception")