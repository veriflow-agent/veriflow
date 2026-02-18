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
import httpx
from typing import Optional
from utils.logger import fact_logger


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

    async def fetch_raw_html(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch raw HTML through the residential proxy.
        Returns HTML string on success, None on failure.
        """
        if not self.enabled or not self.proxy_url:
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

        try:
            async with httpx.AsyncClient(
                proxy=self.proxy_url,
                timeout=timeout,
                follow_redirects=True,
                verify=False,   # some proxy endpoints use self-signed certs
            ) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    content_length = len(response.text)
                    fact_logger.logger.info(
                        f"[ResProxy] Fetched {url} via residential proxy "
                        f"({content_length} chars, status {response.status_code})"
                    )
                    return response.text

                fact_logger.logger.warning(
                    f"[ResProxy] HTTP {response.status_code} for {url}"
                )
                return None

        except httpx.TimeoutException:
            fact_logger.logger.warning(f"[ResProxy] Timeout fetching {url}")
            return None
        except Exception as e:
            fact_logger.logger.warning(f"[ResProxy] Error fetching {url}: {e}")
            return None