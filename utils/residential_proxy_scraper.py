"""
Residential Proxy Scraper

Uses a residential proxy network (Bright Data / Oxylabs) to fetch pages that
block datacenter IPs. This is the fallback for sites like Reuters, Bloomberg,
AP, FT, and WSJ that perform IP reputation checks at the network edge.

Unlike Cloudflare/JS challenges (where CloudScraper helps), these sites simply
reject requests from known datacenter IP ranges -- residential proxies bypass
this by making the request appear to originate from a real ISP subscriber.

Cost: billed per GB of bandwidth. Minimize by only using for known hard domains.
"""

import os
import asyncio
import random
import httpx
from typing import Optional
from utils.logger import fact_logger

RESIDENTIAL_PROXY_MAX_RETRIES = 5
RESIDENTIAL_PROXY_RETRY_DELAY = 7.0  # seconds between retries -- longer gap helps Bright Data
                                      # rotate to a clean exit node from a different ISP pool

# Rotate user agents across retries so consecutive attempts look like different browsers.
# Akamai scores UA + TLS fingerprint together; a different UA on each retry increases the
# chance of hitting a clean node whose fingerprint hasn't been seen recently by Reuters' WAF.
USER_AGENTS = [
    # Chrome 133 on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    # Firefox 147 on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
    # Safari 18.2 on macOS Sequoia 15.2
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    # Edge 144 on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/144.0.0.0",
    # Chrome 133 on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]


class ResidentialProxyScraper:
    """
    Fetches raw HTML through a residential proxy endpoint.
    Used as an HTTP transport only -- content extraction happens
    in the same Playwright-based pipeline as all other strategies.
    """

    def __init__(self):
        self.enabled = False
        self.proxy_url: Optional[str] = None
        self._init()

    def _init(self):
        enabled = os.getenv("RESIDENTIAL_PROXY_ENABLED", "false").lower() == "true"
        host = os.getenv("RESIDENTIAL_PROXY_HOST", "brd.superproxy.io")
        port = os.getenv("RESIDENTIAL_PROXY_PORT", "22225")
        user = os.getenv("RESIDENTIAL_PROXY_USER", "")
        password = os.getenv("RESIDENTIAL_PROXY_PASS", "")

        if not enabled:
            fact_logger.logger.info("Residential proxy disabled (RESIDENTIAL_PROXY_ENABLED not set)")
            return

        if not user or not password:
            fact_logger.logger.warning("Residential proxy enabled but credentials missing")
            return

        self.proxy_url = f"http://{user}:{password}@{host}:{port}"
        self.enabled = True
        fact_logger.logger.info(f"Residential proxy initialized: {host}:{port}")

    async def fetch_raw_html(
        self,
        url: str,
        timeout: int = 30,
        max_retries: int = RESIDENTIAL_PROXY_MAX_RETRIES,
    ) -> Optional[str]:
        """
        Fetch raw HTML through the residential proxy with automatic retries.

        Residential proxies are inherently flaky -- the assigned exit node may
        be temporarily throttled or route through a slow ISP. Retrying with a
        short delay resolves the majority of transient failures without needing
        to fall back to other scrapers that will be blocked by IP reputation checks.

        Returns HTML string on first successful attempt, None if all retries fail.
        """
        if not self.enabled or not self.proxy_url:
            return None

        for attempt in range(1, max_retries + 1):
            # Pick a different UA on each attempt -- Akamai scores UA + TLS fingerprint
            # together, so rotating increases the chance of a clean exit node pairing.
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
                "Referer": "https://www.google.com/",  # Requests without Referer score as bot-likely
            }

            try:
                async with httpx.AsyncClient(
                    proxy=self.proxy_url,
                    timeout=timeout,
                    follow_redirects=True,
                    verify=False,
                ) as client:
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        content_length = len(response.text)
                        fact_logger.logger.info(
                            f"[ResProxy] Fetched {url} (attempt {attempt}/{max_retries}, "
                            f"{content_length} chars, status {response.status_code})"
                        )
                        return response.text

                    fact_logger.logger.warning(
                        f"[ResProxy] HTTP {response.status_code} for {url} "
                        f"(attempt {attempt}/{max_retries})"
                    )
                    # Non-200 but not a network error -- still worth retrying
                    # (residential node may rotate to a different exit IP)

            except httpx.TimeoutException:
                fact_logger.logger.warning(
                    f"[ResProxy] Timeout fetching {url} (attempt {attempt}/{max_retries})"
                )
            except Exception as e:
                fact_logger.logger.warning(
                    f"[ResProxy] Error fetching {url} (attempt {attempt}/{max_retries}): {e}"
                )

            if attempt < max_retries:
                fact_logger.logger.info(
                    f"[ResProxy] Retrying {url} in {RESIDENTIAL_PROXY_RETRY_DELAY}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(RESIDENTIAL_PROXY_RETRY_DELAY)

        fact_logger.logger.warning(
            f"[ResProxy] All {max_retries} attempts failed for {url}"
        )
        return None