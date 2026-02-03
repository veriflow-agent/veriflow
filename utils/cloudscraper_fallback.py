# utils/cloudscraper_fallback.py
"""
CloudScraper Fallback for Cloudflare-Protected Sites

Used as a fallback when both Playwright strategies AND ScrapingBee fail,
specifically for sites using Cloudflare's JavaScript challenges:
- "Just a moment..." interstitial pages
- "Checking your browser..." challenges
- Cloudflare Under Attack Mode

CloudScraper solves Cloudflare's JS challenges by interpreting them
natively in Python, without needing a full browser.

This module is lightweight (no API key required, no per-request cost).
It runs synchronously under the hood, so calls are wrapped in
asyncio.to_thread() for async compatibility.

Setup:
  pip install cloudscraper
  No API key or environment variable needed.
"""

import asyncio
import re
from typing import Optional, Dict

from bs4 import BeautifulSoup, Tag

from utils.logger import fact_logger

# Lazy import -- cloudscraper may not be installed
_cloudscraper_mod = None


def _get_cloudscraper():
    """Lazy-load the cloudscraper module."""
    global _cloudscraper_mod
    if _cloudscraper_mod is None:
        import cloudscraper as _cs
        _cloudscraper_mod = _cs
    return _cloudscraper_mod


class CloudScraperFallback:
    """
    Fallback scraper using CloudScraper for Cloudflare-protected sites.

    Unlike ScrapingBee (which is a paid API), CloudScraper is a free,
    local library that solves Cloudflare JS challenges directly.
    """

    def __init__(self):
        self.enabled = False
        self._scraper = None

        # Stats tracking
        self.stats: Dict = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
        }

        # Try to initialize
        try:
            cs = _get_cloudscraper()
            self._scraper = cs.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                },
                delay=5,  # seconds to wait for Cloudflare challenge
            )
            self.enabled = True
            fact_logger.logger.info(
                "CloudScraper fallback ENABLED"
            )
        except ImportError:
            fact_logger.logger.info(
                "CloudScraper fallback DISABLED (pip install cloudscraper to enable)"
            )
        except Exception as e:
            fact_logger.logger.warning(
                f"CloudScraper fallback DISABLED (init error: {e})"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_raw_html(self, url: str) -> Optional[str]:
        """
        Fetch raw HTML from a Cloudflare-protected URL.

        Runs the synchronous cloudscraper request in a thread so it
        doesn't block the async event loop.

        Args:
            url: The URL to fetch.

        Returns:
            Raw HTML string, or None on failure / block page.
        """
        if not self.enabled or self._scraper is None:
            fact_logger.logger.debug("CloudScraper fallback skipped (not enabled)")
            return None

        self.stats["attempts"] += 1
        fact_logger.logger.info(f"[CloudScraper] Fetching: {url}")

        try:
            # Run synchronous cloudscraper in a thread
            html = await asyncio.wait_for(
                asyncio.to_thread(self._fetch_sync, url),
                timeout=30.0,
            )

            if not html:
                self.stats["failures"] += 1
                fact_logger.logger.warning(
                    f"[CloudScraper] No HTML returned for {url}"
                )
                return None

            # Check if we still got a block page
            soup = BeautifulSoup(html, "lxml")
            if self._is_block_page(soup):
                self.stats["failures"] += 1
                fact_logger.logger.warning(
                    f"[CloudScraper] Block page still detected for {url}"
                )
                return None

            self.stats["successes"] += 1
            fact_logger.logger.info(
                f"[CloudScraper] Fetched {len(html)} chars of HTML from {url}"
            )
            return html

        except asyncio.TimeoutError:
            self.stats["failures"] += 1
            fact_logger.logger.error(
                f"[CloudScraper] Timeout (30s) fetching {url}"
            )
            return None
        except Exception as e:
            self.stats["failures"] += 1
            fact_logger.logger.error(
                f"[CloudScraper] Error fetching {url}: {e}"
            )
            return None

    # ------------------------------------------------------------------
    # Internal: synchronous fetch (runs in thread)
    # ------------------------------------------------------------------

    def _fetch_sync(self, url: str) -> Optional[str]:
        """
        Synchronous fetch using cloudscraper.

        CloudScraper automatically:
        1. Detects Cloudflare challenges
        2. Solves the JavaScript challenge
        3. Returns the real page content
        """
        try:
            response = self._scraper.get(
                url,
                timeout=25,
                headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;"
                        "q=0.9,image/avif,image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                },
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code in (403, 503):
                fact_logger.logger.warning(
                    f"[CloudScraper] HTTP {response.status_code} -- "
                    f"Cloudflare challenge may have failed for {url}"
                )
                return None
            else:
                fact_logger.logger.warning(
                    f"[CloudScraper] HTTP {response.status_code} for {url}"
                )
                return None

        except Exception as e:
            fact_logger.logger.error(
                f"[CloudScraper] Request error for {url}: {e}"
            )
            return None

    # ------------------------------------------------------------------
    # Internal: block page detection
    # ------------------------------------------------------------------

    def _is_block_page(self, soup: BeautifulSoup) -> bool:
        """Detect if we still got a Cloudflare challenge or block page."""
        title = soup.title.string if soup.title else ""
        body_text = soup.body.get_text(strip=True)[:500] if soup.body else ""
        combined = f"{title} {body_text}".lower()

        block_indicators = [
            "just a moment",               # Cloudflare interstitial
            "checking your browser",        # Cloudflare challenge
            "please verify you are a human",
            "access denied",
            "access to this page has been denied",
            "attention required",           # Cloudflare block
            "ray id",                       # Cloudflare error with Ray ID only
            "enable javascript and cookies", # Cloudflare requirement
        ]

        # Check for block indicators
        for indicator in block_indicators:
            if indicator in combined:
                return True

        # Additional check: very short body with Cloudflare markers
        if len(body_text) < 200:
            cf_markers = ["cf-browser-verification", "cf_chl_opt", "challenge-platform"]
            page_html = str(soup)[:2000].lower()
            for marker in cf_markers:
                if marker in page_html:
                    return True

        return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """Return CloudScraper usage statistics."""
        return self.stats.copy()
