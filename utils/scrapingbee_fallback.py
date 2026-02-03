# utils/scrapingbee_fallback.py
"""
ScrapingBee API Fallback for HTTP-Blocked Sites (401/403)

Used as a last resort when all Playwright strategies fail due to:
- Imperva/Incapsula WAF (403 Forbidden) -- e.g., The Hill
- Custom anti-bot blocks (401 Unauthorized) -- e.g., Reuters

Uses premium proxies + JS rendering for maximum bypass capability.
Each request costs ~25 credits (free tier = 1,000 credits/month).

Setup:
  1. Sign up at https://www.scrapingbee.com (free tier available)
  2. Add SCRAPINGBEE_API_KEY to your environment variables
  3. Railway: railway variables set SCRAPINGBEE_API_KEY=your_key

This module is optional -- if no API key is set, it gracefully disables itself.
"""

import os
import re
from typing import Optional, List, Dict

import httpx
from bs4 import BeautifulSoup, Tag

from utils.logger import fact_logger


class ScrapingBeeFallback:
    """
    Fallback scraper using ScrapingBee API for sites that block
    headless browsers at the HTTP level (401/403).
    """

    API_URL = "https://app.scrapingbee.com/api/v1/"

    def __init__(self):
        self.api_key = os.getenv("SCRAPINGBEE_API_KEY", "")
        self.enabled = bool(self.api_key)

        # Stats tracking
        self.stats: Dict = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "credits_used_estimate": 0,
        }

        if self.enabled:
            fact_logger.logger.info(
                "ScrapingBee fallback ENABLED (API key configured)"
            )
        else:
            fact_logger.logger.info(
                "ScrapingBee fallback DISABLED (set SCRAPINGBEE_API_KEY to enable)"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape(self, url: str, selectors: List[str]) -> Optional[str]:
        """
        Scrape a URL using ScrapingBee API.

        Args:
            url: The URL to scrape.
            selectors: Ordered list of CSS selectors to try for content extraction.

        Returns:
            Extracted article text, or None on failure.
        """
        if not self.enabled:
            fact_logger.logger.debug("ScrapingBee fallback skipped (not enabled)")
            return None

        self.stats["attempts"] += 1
        fact_logger.logger.info(f"[ScrapingBee] Attempting fallback scrape: {url}")

        try:
            html = await self._fetch_html(url)

            if not html:
                self.stats["failures"] += 1
                fact_logger.logger.warning(
                    f"[ScrapingBee] No HTML returned for {url}"
                )
                return None

            fact_logger.logger.debug(
                f"[ScrapingBee] Received {len(html)} chars of HTML"
            )

            # Extract article content from the raw HTML
            content = self._extract_content(html, selectors)

            if content and len(content.strip()) > 100:
                self.stats["successes"] += 1
                fact_logger.logger.info(
                    f"[ScrapingBee] Success: extracted {len(content)} chars from {url}"
                )
                return content
            else:
                self.stats["failures"] += 1
                fact_logger.logger.warning(
                    f"[ScrapingBee] Insufficient content extracted from {url} "
                    f"({len(content) if content else 0} chars)"
                )
                return None

        except Exception as e:
            self.stats["failures"] += 1
            fact_logger.logger.error(f"[ScrapingBee] Error scraping {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal: API call
    # ------------------------------------------------------------------

    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        Call ScrapingBee API asynchronously.

        Uses premium proxies (residential IPs) + JS rendering for maximum
        bypass capability against Imperva, Akamai, and other WAFs.

        Credit cost: ~25 per request (render_js=5 + premium_proxy=10-20).
        """
        params = {
            "api_key": self.api_key,
            "url": url,
            "render_js": "true",           # Execute JS for dynamic content
            "premium_proxy": "true",       # Residential proxy for WAF bypass
            "block_resources": "false",    # Don't block -- need full page
            "country_code": "us",          # US IP for US news sites
            "wait": "2000",                # Wait 2s for JS to render
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.get(self.API_URL, params=params)

            # Track estimated credit usage
            self.stats["credits_used_estimate"] += 25

            # Log remaining credits from response headers if available
            remaining = response.headers.get("Spb-remaining-credits")
            if remaining:
                fact_logger.logger.info(
                    f"[ScrapingBee] Credits remaining: {remaining}"
                )

            if response.status_code == 200:
                return response.text
            else:
                fact_logger.logger.warning(
                    f"[ScrapingBee] API returned status {response.status_code} "
                    f"for {url}: {response.text[:200]}"
                )
                return None

        except httpx.TimeoutException:
            fact_logger.logger.error(
                f"[ScrapingBee] Timeout fetching {url}"
            )
            return None
        except Exception as e:
            fact_logger.logger.error(
                f"[ScrapingBee] HTTP error fetching {url}: {e}"
            )
            return None

    # ------------------------------------------------------------------
    # Internal: HTML parsing and content extraction
    # ------------------------------------------------------------------

    def _extract_content(self, html: str, selectors: List[str]) -> Optional[str]:
        """
        Extract article content from raw HTML using CSS selectors.

        Uses the same selector priority as the main Playwright scraper:
        site-specific selectors first, then generic fallbacks.
        """
        soup = BeautifulSoup(html, "lxml")

        # Quick check: is this actually a block page?
        if self._is_block_page(soup):
            fact_logger.logger.warning(
                "[ScrapingBee] Returned page appears to be a block/error page"
            )
            return None

        best_content = ""
        best_score = 0

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    if not isinstance(element, Tag):
                        continue

                    # Remove unwanted elements (same list as Playwright scraper)
                    unwanted_selectors = [
                        "nav", "footer", "header", "aside",
                        ".sidebar", ".navigation", ".nav", ".menu",
                        ".cookie", ".popup", ".modal",
                        ".advertisement", ".ad",
                        ".social-share", ".comments", ".related-articles",
                        '[role="navigation"]', '[role="banner"]',
                        '[role="contentinfo"]',
                        "script", "style", "noscript",
                    ]
                    for sel in unwanted_selectors:
                        for unwanted in element.select(sel):
                            unwanted.decompose()

                    # Extract text with structure
                    text = self._element_to_text(element)

                    # Score the content
                    word_count = len(text.split())
                    paragraph_count = len(
                        [line for line in text.split("\n") if len(line.strip()) > 50]
                    )

                    score = word_count + (paragraph_count * 5)

                    if score > best_score and len(text) > 100:
                        best_score = score
                        best_content = text

            except Exception as e:
                fact_logger.logger.debug(
                    f"[ScrapingBee] Selector '{selector}' failed: {e}"
                )
                continue

        if best_content:
            return self._clean_content(best_content)

        return None

    def _element_to_text(self, element: Tag) -> str:
        """
        Convert a BeautifulSoup element to structured text,
        preserving paragraph breaks and basic formatting.
        """
        lines = []
        seen_texts = set()  # Deduplicate

        for child in element.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
        ):
            text = child.get_text(strip=True)
            if not text or len(text) < 10 or text in seen_texts:
                continue
            seen_texts.add(text)

            if child.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                lines.append(f"\n{text}\n")
            elif child.name == "li":
                lines.append(f"- {text}")
            elif child.name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)
                lines.append("")  # Paragraph break

        result = "\n".join(lines)

        # If structured extraction got very little, fall back to get_text
        if len(result.strip()) < 100:
            result = element.get_text(separator="\n", strip=True)

        return result

    def _is_block_page(self, soup: BeautifulSoup) -> bool:
        """Detect if ScrapingBee returned a block/error page instead of content."""
        title = soup.title.string if soup.title else ""
        body_text = soup.body.get_text(strip=True)[:500] if soup.body else ""

        block_indicators = [
            "access denied",
            "access to this page has been denied",
            "incapsula incident",
            "just a moment",           # Cloudflare challenge
            "checking your browser",   # Cloudflare
            "please verify you are a human",
            "bot detection",
        ]

        combined = f"{title} {body_text}".lower()
        return any(indicator in combined for indicator in block_indicators)

    def _clean_content(self, content: str) -> str:
        """Basic cleaning of extracted content."""
        # Remove excessive whitespace
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        # Remove common noise
        noise_patterns = [
            r"Cookie.*?(?=\n|$)",
            r"Privacy Policy.*?(?=\n|$)",
            r"Terms.*?Service.*?(?=\n|$)",
            r"Subscribe.*?newsletter.*?(?=\n|$)",
            r"Follow us.*?(?=\n|$)",
            r"Download.*?app.*?(?=\n|$)",
            r"Advertisement\n",
            r"Skip to.*?content",
            r"Accept.*?cookies.*?(?=\n|$)",
            r"Back to top.*?(?=\n|$)",
        ]

        for pattern in noise_patterns:
            content = re.sub(pattern, "", content, flags=re.IGNORECASE)

        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
        return content.strip()

    def get_stats(self) -> Dict:
        """Return ScrapingBee usage statistics."""
        return self.stats.copy()
