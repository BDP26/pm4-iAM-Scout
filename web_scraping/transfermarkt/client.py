from __future__ import annotations

import random
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 60

DEFAULT_TOTAL_RETRIES = 5
DEFAULT_BACKOFF_FACTOR = 1.0

STATUS_FORCELIST = (429, 500, 502, 503, 504)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
        }
    )

    retry = Retry(
        total=DEFAULT_TOTAL_RETRIES,
        connect=DEFAULT_TOTAL_RETRIES,
        read=DEFAULT_TOTAL_RETRIES,
        status=DEFAULT_TOTAL_RETRIES,
        backoff_factor=DEFAULT_BACKOFF_FACTOR,
        status_forcelist=STATUS_FORCELIST,
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def fetch_html(
    session: requests.Session,
    url: str,
    timeout: int | float | tuple[float, float] = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT),
    max_attempts: int = 2,
) -> str:
    if isinstance(timeout, (int, float)):
        timeout = (float(timeout), float(timeout))

    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            r = session.get(url, timeout=timeout)

            if r.status_code == 429:
                ra = (r.headers.get("Retry-After") or "").strip()
                wait_s = int(ra) if ra.isdigit() else min(60, 5 * attempt)
                time.sleep(wait_s)

            r.raise_for_status()
            return r.text

        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt >= max_attempts:
                raise

            sleep_s = min(30.0, (2 ** (attempt - 1)) * 1.5) + random.random()
            time.sleep(sleep_s)

    if last_exc:
        raise last_exc
    raise RuntimeError("fetch_html failed without an exception")