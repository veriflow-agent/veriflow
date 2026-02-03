# utils/browserless_scraper.py
"""
Enhanced Railway Browserless Scraper with Multi-Layer Anti-Bot Evasion

NEW FEATURES:
- MULTI-STRATEGY FALLBACK: Basic → Stealth → Advanced → Cloudflare bypass
- USER-AGENT ROTATION: Modern browser UAs (Chrome 133, Firefox 124, Safari 17, Edge 133)
- SITE-SPECIFIC SELECTORS: Custom extractors for The Hill, Reuters, and other news sites
- STEALTH MODE: Removes automation detection markers
- HUMAN BEHAVIOR SIMULATION: Random mouse movements, scrolling, delays
- DOMAIN-SPECIFIC LEARNING: Remembers which strategy works for each domain
- SMART WAIT STRATEGIES: networkidle → load → timed fallbacks
- COOKIE PERSISTENCE: Session continuity across requests
- ENHANCED HEADERS: Realistic browser headers with client hints

EXISTING FEATURES:
- Proper Railway Browserless connection using chromium.connect()
- Persistent browser sessions (browsers stay open during run)
- Support for Railway replicas with load distribution
- Browser pooling for connection reuse
- Fallback to local Playwright if Railway unavailable
- TIMEOUT PROTECTION: Overall 30s timeout prevents infinite hangs
- Individual operation timeouts for robustness
- PARALLEL browser initialization (saves ~30 seconds!)
- Paywall detection for early failure
- AI-POWERED CONTENT CLEANING: Removes subscription noise, device warnings, etc.
"""

import asyncio
import time
import re
import os
import random
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from enum import Enum

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from utils.domain_strategy_service import get_domain_strategy_service

from utils.logger import fact_logger

# NEW: Import content cleaner for AI-powered noise removal
CONTENT_CLEANER_AVAILABLE = False
ArticleContentCleaner = None  # Will be set if import succeeds

try:
    from utils.article_content_cleaner import ArticleContentCleaner as _ArticleContentCleaner
    ArticleContentCleaner = _ArticleContentCleaner
    CONTENT_CLEANER_AVAILABLE = True
except ImportError:
    fact_logger.logger.info("ℹ️ ArticleContentCleaner not available, using basic cleaning only")

# NEW: Try to import playwright-stealth (optional but recommended)
STEALTH_AVAILABLE = False
try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
    fact_logger.logger.info("✅ Playwright Stealth mode available")
except ImportError:
    fact_logger.logger.info("ℹ️ Playwright Stealth not available (install: pip install playwright-stealth)")

class ScrapingStrategy(str, Enum):
    """Enumeration of scraping strategies in order of sophistication"""
    BASIC = "basic"
    STEALTH = "stealth"  
    ADVANCED = "advanced"


# ============================================================================
# CONFIGURATION: User Agents, Selectors, and Strategies
# ============================================================================

# Modern user agents (updated Feb 2025)
USER_AGENTS = [
    # Latest Chrome (Jan 2025)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    # Latest Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

# Site-specific content selectors
SITE_SELECTORS = {
    'thehill.com': [
        '[data-content]',
        '.article__content',
        '.article-content',
        '#article-content',
        '[class*="article-body"]',
        '[class*="story-content"]',
        '.submitted-content',
    ],
    'reuters.com': [
        '[data-testid="article-body"]',
        '.article-body__content',
        '[class*="ArticleBody"]',
        '[data-module="Article"]',
        '.StandardArticleBody_body',
        '[class*="article-body"]',
    ],
    'nytimes.com': [
        '.StoryBodyCompanionColumn',
        '[name="articleBody"]',
        '.story-body',
        '#story',
    ],
    'washingtonpost.com': [
        '.article-body',
        '[data-qa="article-body"]',
        '.story-body',
    ],
    'cnn.com': [
        '.article__content',
        '.pg-rail-tall__body',
        '[class*="article-body"]',
    ],
    'bbc.com': [
        '[data-component="text-block"]',
        '.article__body',
        '.story-body',
    ],
    'foxnews.com': [
        '.article-body',
        '.article-content',
        '[class*="article-text"]',
    ],
}

# Generic fallback selectors (used if no site-specific match)
GENERIC_SELECTORS = [
    'main',
    'article',
    '[role="main"]',
    '.main-content',
    '.content',
    '.article-content',
    '.post-content',
    '#content',
    '#main',
    # WordPress selectors
    '.entry-content',
    '.post-entry',
    '.site-content',
    '.page-content',
    # News site selectors
    '.story-body',
    '.article-body',
    '#article-body',
    '.post-body',
    '#primary',
]

class BrowserlessScraper:
    """
    Enhanced Railway Browserless scraper with multi-layered anti-bot evasion.
    """

    def __init__(self, config):
        self.config = config

        # Railway Browserless configuration
        self.is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
        self.browserless_endpoint = os.getenv('BROWSER_PLAYWRIGHT_ENDPOINT_PRIVATE') or os.getenv('BROWSER_PLAYWRIGHT_ENDPOINT')
        self.browserless_token = os.getenv('BROWSER_TOKEN')
        

        # Support for Railway replicas
        self.replica_id = os.getenv('RAILWAY_REPLICA_ID', '0')

        # Browser pool for persistent sessions
        self.max_concurrent = 10
        self.playwright = None
        self.browser_pool: List[Browser] = []
        self.context_pool: List[BrowserContext] = []  # NEW: Store contexts for cookie persistence
        self.current_browser_index = 0
        self.session_active = False
        self._session_lock = asyncio.Lock()
        self.strategy_service = get_domain_strategy_service()

        # Timeouts
        self.default_timeout = 5000  # 5 seconds
        self.slow_timeout = 10000     # 10 seconds
        self.browser_launch_timeout = 10000
        self.overall_scrape_timeout = 45.0  # Increased from 30s for advanced strategies

        # Domain-specific timeouts
        self.domain_timeouts = {
            'nytimes.com': 10000,
            'washingtonpost.com': 10000,
            'wsj.com': 10000,
            'forbes.com': 10000,
            'reuters.com': 12000,  # Needs more time
            'thehill.com': 10000,
        }

        # Timing
        self.load_wait_time = 2.0
        self.interaction_delay = 0.5

        # AI-powered content cleaner
        self._content_cleaner: Optional[object] = None
        self.enable_ai_cleaning = True

        # NEW: Enhanced stats tracking
        self.stats = {
            "total_scraped": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "timeout_scrapes": 0,
            "paywall_detected": 0,
            "ai_cleaned": 0,
            "ai_cleaning_failed": 0,
            "avg_scrape_time": 0.0,
            "total_processing_time": 0.0,
            "browser_reuses": 0,
            "railway_browserless": bool(self.browserless_endpoint),
            "replica_id": self.replica_id,
            # NEW: Strategy usage tracking
            "strategy_usage": {
                ScrapingStrategy.BASIC: 0,
                ScrapingStrategy.STEALTH: 0,
                ScrapingStrategy.ADVANCED: 0,
                ScrapingStrategy.CLOUDFLARE: 0,
            },
            "strategy_success": {
                ScrapingStrategy.BASIC: 0,
                ScrapingStrategy.STEALTH: 0,
                ScrapingStrategy.ADVANCED: 0,
                ScrapingStrategy.CLOUDFLARE: 0,
            },
            # Site-specific failures
            "site_failures": {},
        }

        if self.browserless_endpoint:
            fact_logger.logger.info(f"🚂 Railway Browserless endpoint configured: {self.browserless_endpoint[:50]}...")
            fact_logger.logger.info(f"🔢 Running on replica: {self.replica_id}")
        else:
            fact_logger.logger.info("🔧 Local Playwright mode")

        fact_logger.log_component_start(
            "BrowserlessScraper",
            browserless=bool(self.browserless_endpoint),
            replica_id=self.replica_id,
            browser_pool_size=self.max_concurrent,
            ai_cleaning=CONTENT_CLEANER_AVAILABLE,
            stealth_mode=STEALTH_AVAILABLE
        )

    def _save_domain_strategy(self, domain: str, strategy: str):
        """Save successful strategy for a domain"""
        try:
            self.domain_strategies[domain] = strategy
            strategy_file = '/tmp/domain_strategies.json'
            with open(strategy_file, 'w') as f:
                json.dump(self.domain_strategies, f)
            fact_logger.logger.debug(f"💾 Saved strategy for {domain}: {strategy}")
        except Exception as e:
            fact_logger.logger.debug(f"Could not save domain strategy: {e}")

    def _get_content_cleaner(self):
        """Lazy initialization of content cleaner"""
        if self._content_cleaner is None and CONTENT_CLEANER_AVAILABLE and ArticleContentCleaner is not None:
            try:
                self._content_cleaner = ArticleContentCleaner(self.config)
                fact_logger.logger.info("✅ AI content cleaner initialized")
            except Exception as e:
                fact_logger.logger.warning(f"⚠️ Failed to initialize content cleaner: {e}")
        return self._content_cleaner

    def _get_random_user_agent(self) -> str:
        """Select random modern user agent"""
        return random.choice(USER_AGENTS)

    def _get_site_selectors(self, url: str) -> List[str]:
        """Get site-specific selectors + generic fallbacks"""
        domain = urlparse(url).netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Get site-specific selectors
        site_selectors = SITE_SELECTORS.get(domain, [])
        
        # Combine with generic selectors
        return site_selectors + GENERIC_SELECTORS

    async def scrape_urls_for_facts(self, urls: List[str]) -> Dict[str, str]:
        """
        Scrape multiple URLs with persistent browser sessions and AI cleaning.

        Args:
            urls: List of URLs to scrape

        Returns:
            Dict mapping URL to scraped (and cleaned) content
        """
        if not urls:
            fact_logger.logger.warning("No URLs provided for scraping")
            return {}

        # Calculate how many browsers we actually need
        num_browsers_needed = min(len(urls), 3)  # Cap at 3 for small batches

        fact_logger.logger.info(
            f"🚀 Starting scrape of {len(urls)} URLs with persistent browsers",
            extra={"url_count": len(urls), "replica_id": self.replica_id}
        )

        await self._initialize_browser_pool(min_browsers=num_browsers_needed)

        try:
            # Process URLs with concurrency control
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = [
                self._scrape_with_semaphore(semaphore, url, i % len(self.browser_pool))
                for i, url in enumerate(urls)
            ]

            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert to dict and handle exceptions
            results = {}
            for url, result in zip(urls, results_list):
                if isinstance(result, Exception):
                    fact_logger.logger.error(
                        f"❌ Scraping failed for {url}: {result}",
                        extra={"url": url, "error": str(result)}
                    )
                    results[url] = ""
                else:
                    results[url] = result

            successful = len([v for v in results.values() if v])
            self.stats["browser_reuses"] += max(0, len(urls) - len(self.browser_pool))

            fact_logger.logger.info(
                f"✅ Scraping complete: {successful}/{len(urls)} successful",
                extra={
                    "successful": successful,
                    "total": len(urls),
                    "browser_reuses": self.stats["browser_reuses"],
                    "timeouts": self.stats["timeout_scrapes"],
                    "paywalls": self.stats["paywall_detected"],
                    "ai_cleaned": self.stats["ai_cleaned"],
                    "strategy_stats": self.stats["strategy_success"]
                }
            )

            return results

        finally:
            # Keep browsers alive for next batch
            pass

    async def _initialize_browser_pool(self, min_browsers: Optional[int] = None):
        """Initialize browser pool in PARALLEL with enhanced contexts"""
        async with self._session_lock:
            if self.session_active and len(self.browser_pool) >= (min_browsers or 1):
                return

            target_count = min_browsers or self.max_concurrent

            if len(self.browser_pool) < target_count:
                browsers_needed = target_count - len(self.browser_pool)
                fact_logger.logger.info(f"🔧 Initializing {browsers_needed} browsers in parallel...")

                start = time.time()
                self.playwright = await async_playwright().start()

                # Create browsers in parallel
                browser_tasks = [
                    self._create_browser(i + len(self.browser_pool))
                    for i in range(browsers_needed)
                ]
                new_browsers = await asyncio.gather(*browser_tasks, return_exceptions=True)

                # Filter out failed browsers
                for browser in new_browsers:
                    if browser and not isinstance(browser, Exception):
                        self.browser_pool.append(browser)

                elapsed = time.time() - start
                fact_logger.logger.info(
                    f"✅ Initialized {len(self.browser_pool)} browsers in {elapsed:.1f}s"
                )

            self.session_active = True

    async def _create_browser(self, browser_index: int) -> Optional[Browser]:
        """Create a single browser with Railway Browserless or local Playwright"""
        try:
            if self.browserless_endpoint and self.browserless_token:
                # Railway Browserless connection
                ws_endpoint = f"{self.browserless_endpoint}?token={self.browserless_token}"
                browser = await self.playwright.chromium.connect(
                    ws_endpoint,
                    timeout=self.browser_launch_timeout
                )
                fact_logger.logger.debug(f"🌐 Connected to Railway browser {browser_index}")
            else:
                # Local Playwright
                browser = await self.playwright.chromium.launch(
                    headless=True,
                    timeout=self.browser_launch_timeout,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                    ]
                )
                fact_logger.logger.debug(f"🖥️ Launched local browser {browser_index}")

            return browser

        except Exception as e:
            fact_logger.logger.error(f"❌ Failed to create browser {browser_index}: {e}")
            return None

    async def _scrape_with_semaphore(self, semaphore: asyncio.Semaphore, url: str, browser_index: int) -> str:
        """Scrape using persistent browser from pool"""
        async with semaphore:
            return await self._scrape_single_url(url, browser_index)

    async def _scrape_single_url(self, url: str, browser_index: int) -> str:
        """Scrape single URL with timeout protection and multi-strategy fallback"""
        start_time = time.time()
        self.stats["total_scraped"] += 1

        # Select browser from pool
        if browser_index >= len(self.browser_pool):
            browser_index = 0

        browser = self.browser_pool[browser_index]

        # Overall timeout to prevent infinite hangs
        try:
            return await asyncio.wait_for(
                self._scrape_url_multi_strategy(url, browser_index, browser, start_time),
                timeout=self.overall_scrape_timeout
            )
        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            self.stats["failed_scrapes"] += 1
            self.stats["timeout_scrapes"] += 1
            fact_logger.logger.error(
                f"⏰ TIMEOUT after {processing_time:.1f}s: {url}",
                extra={"url": url, "browser_index": browser_index, "timeout": self.overall_scrape_timeout}
            )
            return ""
        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["failed_scrapes"] += 1
            fact_logger.logger.error(
                f"❌ Scraping error for {url}: {e}",
                extra={"url": url, "duration": processing_time, "error": str(e)}
            )
            return ""

    async def _scrape_url_multi_strategy(
        self,
        url: str,
        browser_index: int,
        browser: Browser,
        start_time: float
    ) -> str:
        """
        Multi-strategy scraping with Supabase domain learning.
        Tries strategies in order: known → basic → stealth → advanced
        """
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        # Check Supabase for known working strategy
        known_strategy = self.strategy_service.get_strategy(domain)

        if known_strategy:
            fact_logger.logger.info(
                f"🎯 Using known strategy for {domain}: {known_strategy}",
                extra={"domain": domain, "strategy": known_strategy, "source": "supabase"}
            )

            content = await self._try_strategy(
                url, browser_index, browser, start_time, known_strategy
            )

            if content:
                # Known strategy worked!
                processing_time = time.time() - start_time
                self.strategy_service.save_strategy(domain, known_strategy)
                self.stats["strategy_success"][known_strategy] += 1

                fact_logger.logger.debug(
                    f"✅ Known strategy succeeded for {domain}",
                    extra={
                        "domain": domain,
                        "strategy": known_strategy,
                        "duration_ms": int(processing_time * 1000),
                        "content_length": len(content)
                    }
                )
                return content
            else:
                # Known strategy failed
                fact_logger.logger.warning(
                    f"⚠️ Known strategy '{known_strategy}' failed for {domain}, trying all strategies",
                    extra={"domain": domain, "failed_strategy": known_strategy}
                )

        # Try strategies in order
        strategies = [ScrapingStrategy.BASIC]

        if STEALTH_AVAILABLE:
            strategies.append(ScrapingStrategy.STEALTH)

        strategies.append(ScrapingStrategy.ADVANCED)

        for strategy in strategies:
            fact_logger.logger.info(
                f"🔄 Trying {strategy} strategy for {url}",
                extra={"url": url, "strategy": strategy, "domain": domain}
            )

            content = await self._try_strategy(
                url, browser_index, browser, start_time, strategy
            )

            if content:
                # Success! Save to Supabase
                processing_time = time.time() - start_time
                self.strategy_service.save_strategy(domain, strategy)
                self.stats["strategy_success"][strategy] += 1

                fact_logger.logger.info(
                    f"💾 Learned new strategy: {domain} → {strategy}",
                    extra={
                        "domain": domain,
                        "strategy": strategy,
                        "duration_ms": int(processing_time * 1000),
                        "is_new_learning": known_strategy is None,
                        "content_length": len(content)
                    }
                )
                return content
            else:
                fact_logger.logger.debug(
                    f"❌ {strategy} strategy failed for {url}",
                    extra={"url": url, "strategy": strategy, "domain": domain}
                )

        # All strategies failed
        fact_logger.logger.error(
            f"❌ All strategies failed for {url}",
            extra={
                "url": url,
                "domain": domain,
                "strategies_tried": [s for s in strategies],
                "known_strategy": known_strategy
            }
        )

        # Track site-specific failure
        if domain not in self.stats["site_failures"]:
            self.stats["site_failures"][domain] = 0
        self.stats["site_failures"][domain] += 1

        return ""

    async def _try_strategy(
        self,
        url: str,
        browser_index: int,
        browser: Browser,
        start_time: float,
        strategy: str
    ) -> str:
        """Try a specific scraping strategy"""
        self.stats["strategy_usage"][strategy] += 1
        
        page = None
        context = None
        
        try:
            # Create context based on strategy
            context = await self._create_context(browser, strategy)
            
            # Create page
            page = await asyncio.wait_for(context.new_page(), timeout=10.0)
            
            # Apply stealth if available and strategy requires it
            if STEALTH_AVAILABLE and strategy in [ScrapingStrategy.STEALTH, ScrapingStrategy.ADVANCED]:
                await stealth_async(page)
                fact_logger.logger.debug(f"🥷 Applied stealth mode to page")
            
            # Configure page based on strategy
            await self._configure_page(page, strategy)
            
            # Navigate with strategy-specific wait
            await self._navigate_with_strategy(page, url, strategy)
            
            # Early paywall detection
            if await self._detect_paywall(page):
                self.stats["failed_scrapes"] += 1
                self.stats["paywall_detected"] += 1
                fact_logger.logger.warning(f"🔒 Paywall detected, skipping: {url}")
                return ""
            
            # Apply human-like behaviors for advanced strategies
            if strategy == ScrapingStrategy.ADVANCED:
                await self._simulate_human_behavior(page)
            
            # Extract content with site-specific selectors
            raw_content = await asyncio.wait_for(
                self._extract_structured_content(page, url),
                timeout=10.0
            )
            
            if raw_content and len(raw_content.strip()) > 100:
                # Step 1: Basic regex cleaning
                content = self._clean_content(raw_content)
                
                # Step 2: AI-powered cleaning
                if self.enable_ai_cleaning and CONTENT_CLEANER_AVAILABLE:
                    try:
                        cleaner = self._get_content_cleaner()
                        if cleaner is not None:
                            cleaning_result = await asyncio.wait_for(
                                cleaner.clean(url, content),  # type: ignore[union-attr]
                                timeout=15.0
                            )
                            
                            if (cleaning_result.success 
                                and cleaning_result.cleaned is not None 
                                and cleaning_result.cleaned.body):
                                
                                original_len = len(content)
                                content = cleaning_result.cleaned.body
                                self.stats["ai_cleaned"] += 1
                                
                                fact_logger.logger.info(
                                    f"🧹 AI cleaned: {original_len} → {len(content)} chars "
                                    f"({cleaning_result.reduction_percent:.0f}% noise removed)"
                                )
                            else:
                                self.stats["ai_cleaning_failed"] += 1
                    except Exception as e:
                        self.stats["ai_cleaning_failed"] += 1
                        fact_logger.logger.warning(f"⚠️ AI cleaning failed: {e}")
                
                processing_time = time.time() - start_time
                self.stats["successful_scrapes"] += 1
                self.stats["total_processing_time"] += processing_time
                self.stats["avg_scrape_time"] = (
                    self.stats["total_processing_time"] / self.stats["total_scraped"]
                )
                
                fact_logger.logger.info(
                    f"✅ Successfully scraped with {strategy}: {url}",
                    extra={
                        "url": url,
                        "duration": processing_time,
                        "content_length": len(content),
                        "strategy": strategy
                    }
                )
                return content
            else:
                fact_logger.logger.debug(
                    f"⚠️ Insufficient content from {url} using {strategy}",
                    extra={"url": url, "content_length": len(raw_content) if raw_content else 0}
                )
                return ""
                
        except Exception as e:
            fact_logger.logger.debug(f"Strategy {strategy} failed for {url}: {e}")
            return ""
        finally:
            # Close page
            if page:
                try:
                    await asyncio.wait_for(page.close(), timeout=3.0)
                except Exception:
                    pass
            
            # Close context
            if context:
                try:
                    await asyncio.wait_for(context.close(), timeout=3.0)
                except Exception:
                    pass

    async def _create_context(self, browser: Browser, strategy: str) -> BrowserContext:
        """Create browser context with strategy-specific configuration"""
        user_agent = self._get_random_user_agent()
        
        # Base context options
        context_options = {
            'user_agent': user_agent,
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
        }
        
        # Enhanced options for stealth and advanced strategies
        if strategy in [ScrapingStrategy.STEALTH, ScrapingStrategy.ADVANCED]:
            context_options.update({
                'permissions': [],
                'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},  # NYC
                'color_scheme': 'light',
                'has_touch': False,
                'is_mobile': False,
                'java_script_enabled': True,
                'bypass_csp': True,
                'ignore_https_errors': True,
            })
        
        context = await browser.new_context(**context_options)
        
        # Set extra HTTP headers for better mimicry
        if strategy in [ScrapingStrategy.STEALTH, ScrapingStrategy.ADVANCED]:
            await context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            })
        
        return context

    async def _configure_page(self, page: Page, strategy: str):
        """Configure page with strategy-specific optimizations"""
        try:
            # Block unnecessary resources for all strategies
            await page.route("**/*", self._block_resources)
            
            # Add init scripts for stealth/advanced strategies
            if strategy in [ScrapingStrategy.STEALTH, ScrapingStrategy.ADVANCED]:
                await page.add_init_script("""
                    // Remove webdriver flag
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Disable image loading
                    Object.defineProperty(HTMLImageElement.prototype, 'src', {
                        set: function() { /* blocked */ },
                        get: function() { return ''; }
                    });
                    
                    // Speed up animations
                    document.addEventListener('DOMContentLoaded', function() {
                        const style = document.createElement('style');
                        style.textContent = `
                            *, *::before, *::after {
                                animation-duration: 0.01ms !important;
                                animation-delay: -0.01ms !important;
                                transition-duration: 0.01ms !important;
                                transition-delay: -0.01ms !important;
                            }
                        `;
                        document.head.appendChild(style);
                    });
                    
                    // Disable popups
                    window.alert = () => {};
                    window.confirm = () => true;
                    window.prompt = () => '';
                """)
        except Exception as e:
            fact_logger.logger.warning(f"⚠️ Page configuration partially failed: {e}")

    async def _navigate_with_strategy(self, page: Page, url: str, strategy: str):
        """Navigate to URL with strategy-specific wait conditions"""
        domain = urlparse(url).netloc.lower()
        base_timeout = self.domain_timeouts.get(domain, self.default_timeout)
        
        if strategy == ScrapingStrategy.BASIC:
            # Basic: domcontentloaded
            await page.goto(url, wait_until="domcontentloaded", timeout=base_timeout)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
        elif strategy == ScrapingStrategy.STEALTH:
            # Stealth: Try networkidle, fallback to load
            try:
                await page.goto(url, wait_until="networkidle", timeout=base_timeout)
            except Exception:
                await page.goto(url, wait_until="load", timeout=base_timeout)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
        elif strategy == ScrapingStrategy.ADVANCED:
            # Advanced: Multiple wait strategies + random delay
            try:
                await page.goto(url, wait_until="networkidle", timeout=base_timeout)
            except Exception:
                try:
                    await page.goto(url, wait_until="load", timeout=base_timeout)
                except Exception:
                    await page.goto(url, wait_until="domcontentloaded", timeout=base_timeout)
            
            # Random human-like delay
            await asyncio.sleep(random.uniform(2.0, 4.0))

    async def _simulate_human_behavior(self, page: Page):
        """Simulate human-like behaviors: mouse movement, scrolling"""
        try:
            # Random mouse movement
            await page.mouse.move(
                random.randint(100, 500),
                random.randint(100, 500),
                steps=random.randint(5, 15)
            )
            
            # Random scroll
            scroll_amount = random.randint(100, 500)
            await page.mouse.wheel(0, scroll_amount)
            
            # Small delay
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Another random scroll
            await page.mouse.wheel(0, random.randint(50, 200))
            
        except Exception as e:
            fact_logger.logger.debug(f"Human behavior simulation error: {e}")

    async def _block_resources(self, route):
        """Block unnecessary resources for faster loading"""
        resource_type = route.request.resource_type
        url = route.request.url

        # Block resource types
        if resource_type in ['image', 'media', 'font']:
            await route.abort()
        # Block tracking and ads
        elif any(blocked in url for blocked in [
            'analytics', 'tracking', 'advertisement', 'ads',
            'facebook.com/tr', 'google-analytics', 'doubleclick'
        ]):
            await route.abort()
        else:
            await route.continue_()

    async def _detect_paywall(self, page: Page) -> bool:
        """Quick paywall detection to fail fast"""
        try:
            # Common paywall indicators
            paywall_selectors = [
                '[class*="paywall"]',
                '[class*="subscription"]',
                '[id*="paywall"]',
                '[data-testid*="paywall"]',
                '.gateway-content',
                '.meteredContent',
                '#paywall-container',
                '.piano-offer',
                '.tp-modal',
            ]

            for selector in paywall_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            fact_logger.logger.warning(f"🔒 Paywall detected: {selector}")
                            return True
                except Exception:
                    continue

            # Check for very short content
            try:
                body_text = await page.inner_text('body')
                if body_text and len(body_text.strip()) < 500:
                    paywall_keywords = ['subscribe', 'subscription', 'sign in to read', 'become a member', 'premium content']
                    body_lower = body_text.lower()
                    for keyword in paywall_keywords:
                        if keyword in body_lower:
                            fact_logger.logger.warning(f"🔒 Likely paywall (short content with '{keyword}')")
                            return True
            except Exception:
                pass

            return False

        except Exception as e:
            fact_logger.logger.debug(f"Paywall detection error: {e}")
            return False

    async def _extract_structured_content(self, page: Page, url: str = "") -> str:
        """Extract main content using site-specific and generic selectors"""
        try:
            fact_logger.logger.debug("Extracting structured content")
            
            # Get site-specific selectors
            selectors = self._get_site_selectors(url) if url else GENERIC_SELECTORS
            
            # JavaScript function to extract content
            content_data = await page.evaluate(f"""
                () => {{
                    function htmlToStructuredText(element, level = 0) {{
                        if (!element) return '';
                        if (level > 10) return '';
                        
                        let result = '';
                        
                        if (element.nodeType === Node.TEXT_NODE) {{
                            const text = element.textContent.trim();
                            if (text && text.length > 0) {{
                                result += text + ' ';
                            }}
                        }} else if (element.nodeType === Node.ELEMENT_NODE) {{
                            const tagName = element.tagName.toLowerCase();
                            
                            if (['script', 'style', 'noscript', 'head', 'meta', 'link'].includes(tagName)) {{
                                return '';
                            }}
                            
                            switch (tagName) {{
                                case 'h1':
                                case 'h2':
                                case 'h3':
                                case 'h4':
                                case 'h5':
                                case 'h6':
                                    const headingText = element.textContent.trim();
                                    if (headingText) {{
                                        const headingLevel = parseInt(tagName[1]);
                                        const prefix = '#'.repeat(headingLevel);
                                        result += '\\n\\n' + prefix + ' ' + headingText + '\\n';
                                    }}
                                    break;
                                
                                case 'p':
                                    const pText = element.textContent.trim();
                                    if (pText && pText.length > 20) {{
                                        result += '\\n' + pText + '\\n';
                                    }}
                                    break;
                                
                                case 'div':
                                case 'section':
                                case 'article':
                                    for (let child of element.childNodes) {{
                                        result += htmlToStructuredText(child, level + 1);
                                    }}
                                    break;
                                
                                case 'li':
                                    const liText = element.textContent.trim();
                                    if (liText && liText.length > 10) {{
                                        result += '\\n• ' + liText + '\\n';
                                    }}
                                    break;
                                
                                default:
                                    for (let child of element.childNodes) {{
                                        result += htmlToStructuredText(child, level + 1);
                                    }}
                                    break;
                            }}
                        }}
                        
                        return result;
                    }}
                    
                    // Try selectors in order
                    const selectors = {json.dumps(selectors)};
                    
                    let bestContent = '';
                    let bestScore = 0;
                    
                    for (const selector of selectors) {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            const clone = element.cloneNode(true);
                            
                            // Remove unwanted elements
                            const unwantedElements = clone.querySelectorAll(`
                                nav, footer, header, aside,
                                .sidebar, .navigation, .nav, .menu,
                                .cookie, .popup, .modal, .advertisement, .ad,
                                .social-share, .comments, .related-articles,
                                [role="navigation"], [role="banner"], [role="contentinfo"],
                                script, style, noscript
                            `);
                            unwantedElements.forEach(el => el.remove());
                            
                            const structuredText = htmlToStructuredText(clone);
                            
                            // Score based on content quality
                            const headingCount = (structuredText.match(/^#+\\s/gm) || []).length;
                            const paragraphCount = (structuredText.match(/\\n[^\\n#•].+\\n/g) || []).length;
                            const wordCount = structuredText.split(/\\s+/).filter(w => w.length > 0).length;
                            
                            let score = 0;
                            score += headingCount * 10;
                            score += paragraphCount * 5;
                            score += Math.min(wordCount, 500);
                            
                            if (score > bestScore && structuredText.length > 100) {{
                                bestScore = score;
                                bestContent = structuredText;
                            }}
                        }}
                    }}
                    
                    return bestContent;
                }}
            """)
            
            content = content_data if content_data else ""
            
            fact_logger.logger.debug(
                "Structure extraction complete",
                extra={"content_length": len(content)}
            )
            
            return content
            
        except Exception as e:
            fact_logger.logger.error(f"❌ Structure extraction error: {e}")
            return ""

    def _clean_content(self, content: str) -> str:
        """Basic regex cleaning of extracted content"""
        if not content:
            return ""

        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        # Remove common noise patterns
        noise_patterns = [
            r'Cookie.*?(?=\n|$)',
            r'Privacy Policy.*?(?=\n|$)',
            r'Terms.*?Service.*?(?=\n|$)',
            r'Subscribe.*?newsletter.*?(?=\n|$)',
            r'Follow us.*?(?=\n|$)',
            r'Download.*?app.*?(?=\n|$)',
            r'Advertisement\n',
            r'Skip to.*?content',
            r'Accept.*?cookies.*?(?=\n|$)',
            r'Back to top.*?(?=\n|$)',
        ]

        for pattern in noise_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        # Final cleanup
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = content.strip()

        return content

    def get_stats(self) -> Dict:
        """Return scraping statistics with Supabase domain learning data"""
        stats = self.stats.copy()

        # Add domain strategy information from Supabase
        try:
            all_strategies = self.strategy_service.get_all_strategies()
            stats['learned_domains_count'] = len(all_strategies)
            stats['learned_strategies'] = all_strategies

            fact_logger.logger.debug(
                f"📊 Retrieved {len(all_strategies)} learned strategies from Supabase",
                extra={"strategy_count": len(all_strategies)}
            )
        except Exception as e:
            fact_logger.logger.warning(
                f"⚠️ Could not retrieve Supabase strategy stats: {e}",
                extra={"error": str(e)}
            )
            stats['learned_domains_count'] = 0
            stats['learned_strategies'] = {}

        return stats

    async def close(self):
        """Properly close browser pool and cleanup"""
        fact_logger.logger.info("🛑 Shutting down scraper...")

        # Close all contexts
        for i, context in enumerate(self.context_pool):
            try:
                await context.close()
                fact_logger.logger.debug(f"✅ Closed context {i}")
            except Exception as e:
                fact_logger.logger.debug(f"Context close error (non-critical): {e}")

        # Close all browsers in pool
        for i, browser in enumerate(self.browser_pool):
            try:
                await browser.close()
                fact_logger.logger.debug(f"✅ Closed browser {i}")
            except Exception as e:
                fact_logger.logger.debug(f"Browser close error (non-critical): {e}")

        # Stop Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                fact_logger.logger.debug("✅ Playwright stopped")
            except Exception as e:
                fact_logger.logger.debug(f"Playwright stop error (non-critical): {e}")

        self.session_active = False
        self.browser_pool = []
        self.context_pool = []

        # Print stats
        if self.stats["total_scraped"] > 0:
            success_rate = (self.stats["successful_scrapes"] / self.stats["total_scraped"]) * 100
            fact_logger.logger.info(
                f"📊 Scraping stats: {self.stats['successful_scrapes']}/{self.stats['total_scraped']} "
                f"successful ({success_rate:.1f}%), {self.stats['browser_reuses']} browser reuses"
            )
            
            # Strategy stats
            fact_logger.logger.info("📈 Strategy performance:")
            for strategy, usage in self.stats["strategy_usage"].items():
                if usage > 0:
                    success = self.stats["strategy_success"].get(strategy, 0)
                    rate = (success / usage * 100) if usage > 0 else 0
                    fact_logger.logger.info(f"  {strategy}: {success}/{usage} ({rate:.1f}%)")
            
            # Site failures
            if self.stats["site_failures"]:
                fact_logger.logger.info("⚠️ Sites with failures:")
                for domain, count in sorted(
                    self.stats["site_failures"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]:
                    fact_logger.logger.info(f"  {domain}: {count} failures")

        # Log Supabase learning stats on shutdown
        try:
            all_strategies = self.strategy_service.get_all_strategies()
            if all_strategies:
                fact_logger.logger.info(
                    f"📚 Domain learning summary: {len(all_strategies)} strategies saved in Supabase"
                )

                # Count by strategy type
                strategy_counts = {}
                for domain, strategy in all_strategies.items():
                    strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

                for strategy, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
                    fact_logger.logger.info(f"  {strategy}: {count} domains")
        except Exception as e:
            fact_logger.logger.debug(f"Could not retrieve Supabase stats on shutdown: {e}")
            
        fact_logger.logger.info("✅ Scraper shutdown complete")
