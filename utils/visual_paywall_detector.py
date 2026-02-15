# utils/visual_paywall_detector.py
"""
Visual Paywall Detector -- GPT-4o-mini Vision Analysis

When the scraper extracts suspiciously short content from a page,
this module takes a full-page screenshot using Playwright and sends
it to GPT-4o-mini for visual paywall detection.

HOW IT WORKS:
1. Playwright page.screenshot(full_page=True) captures the ENTIRE
   scrollable page as PNG bytes -- no extra library needed.
2. PNG bytes are base64-encoded and sent to GPT-4o-mini vision.
3. The model analyzes the screenshot for visual paywall indicators:
   blurred text, subscription overlays, truncated content, etc.
4. Returns a structured result with confidence score.

COST:
- GPT-4o-mini vision is very cheap (~0.15c per 1000 input tokens).
- A typical full-page screenshot at low detail = ~85 tokens = negligible.
- Only triggered on "suspicious" pages, not every scrape.

INTEGRATION:
  Called from BrowserlessScraper._try_strategy() when extracted content
  is shorter than a configurable threshold (e.g. 800 chars).

USAGE:
    from utils.visual_paywall_detector import VisualPaywallDetector

    detector = VisualPaywallDetector()
    result = await detector.detect(page, url, content_length=350)

    if result.is_paywalled:
        logger.warning(f"Visual paywall detected: {result.description}")
"""

import base64
import json
import os
from typing import Optional
from pydantic import BaseModel, Field

from playwright.async_api import Page

from utils.logger import fact_logger
from prompts.visual_paywall_detector_prompts import SYSTEM_PROMPT, USER_PROMPT


# ============================================================================
# RESULT MODEL
# ============================================================================

class PaywallDetectionResult(BaseModel):
    """Structured result from visual paywall analysis"""

    is_paywalled: bool = Field(
        default=False,
        description="Whether a paywall was detected"
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score 0.0-1.0"
    )
    paywall_type: str = Field(
        default="none",
        description="Type: hard, soft, metered, registration, none"
    )
    description: str = Field(
        default="",
        description="Brief explanation of what was detected"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if detection failed"
    )


# ============================================================================
# CONFIGURATION
# ============================================================================

# Content length threshold (chars) -- if extracted content is shorter
# than this, trigger visual detection. Tune based on your experience.
DEFAULT_SHORT_CONTENT_THRESHOLD = 800

# Screenshot settings
SCREENSHOT_TIMEOUT = 10.0  # seconds
# We use JPEG for smaller file size (vision models handle it fine)
SCREENSHOT_TYPE = "jpeg"
SCREENSHOT_QUALITY = 60  # 0-100, lower = smaller file = faster upload

# Vision model settings
VISION_MODEL = "gpt-4o-mini"
VISION_MAX_TOKENS = 300  # Response is just a small JSON
VISION_DETAIL = "low"  # "low" = 85 tokens, plenty for paywall detection


# ============================================================================
# DETECTOR CLASS
# ============================================================================

class VisualPaywallDetector:
    """
    Detects paywalls by taking a full-page screenshot and
    analyzing it with GPT-4o-mini vision.

    Uses the OpenAI API directly (not LangChain) because
    LangChain's image message handling adds unnecessary complexity
    for a simple single-shot vision call.
    """

    def __init__(
        self,
        short_content_threshold: int = DEFAULT_SHORT_CONTENT_THRESHOLD,
    ):
        self.short_content_threshold = short_content_threshold
        self._openai_client = None

        fact_logger.logger.info(
            f"VisualPaywallDetector initialized "
            f"(threshold={short_content_threshold} chars, "
            f"model={VISION_MODEL})"
        )

    def _get_openai_client(self):
        """
        Lazy-init OpenAI client.

        Uses the same key rotation env vars as the rest of the app:
        OPENAI_API_KEYS (comma-separated) or OPENAI_API_KEY.
        """
        if self._openai_client is None:
            try:
                from openai import AsyncOpenAI

                # Grab a key -- use the rotator if available, else env var
                api_key = None
                try:
                    from utils.openai_client import _get_rotator
                    api_key = _get_rotator().next_key()
                except Exception:
                    api_key = os.getenv("OPENAI_API_KEY", "")

                if not api_key:
                    fact_logger.logger.error(
                        "No OpenAI API key available for visual paywall detection"
                    )
                    return None

                self._openai_client = AsyncOpenAI(api_key=api_key)
            except ImportError:
                fact_logger.logger.error(
                    "openai package not installed. "
                    "Run: pip install openai"
                )
                return None

        return self._openai_client

    def should_check(self, content_length: int) -> bool:
        """
        Decide whether to trigger visual detection.

        Call this BEFORE taking the screenshot to avoid unnecessary
        overhead on pages with normal-length content.

        Args:
            content_length: Length of extracted article text in chars

        Returns:
            True if content seems suspiciously short
        """
        return content_length < self.short_content_threshold

    async def take_screenshot(self, page: Page) -> Optional[bytes]:
        """
        Take a full-page screenshot using Playwright.

        Playwright's page.screenshot(full_page=True) captures the
        ENTIRE scrollable page, not just the viewport. Returns raw
        image bytes (JPEG).

        Args:
            page: Active Playwright page object

        Returns:
            JPEG bytes, or None on failure
        """
        try:
            import asyncio

            screenshot_bytes = await asyncio.wait_for(
                page.screenshot(
                    full_page=True,
                    type=SCREENSHOT_TYPE,
                    quality=SCREENSHOT_QUALITY,
                ),
                timeout=SCREENSHOT_TIMEOUT
            )

            size_kb = len(screenshot_bytes) / 1024
            fact_logger.logger.info(
                f"Full-page screenshot captured: {size_kb:.1f} KB"
            )

            return screenshot_bytes

        except Exception as e:
            fact_logger.logger.warning(
                f"Screenshot capture failed: {type(e).__name__}: {e}"
            )
            return None

    async def analyze_screenshot(
        self,
        screenshot_bytes: bytes,
        url: str,
        content_length: int,
    ) -> PaywallDetectionResult:
        """
        Send screenshot to GPT-4o-mini vision for paywall analysis.

        Args:
            screenshot_bytes: Raw JPEG bytes from take_screenshot()
            url: The page URL (for context in the prompt)
            content_length: How many chars were extracted (for context)

        Returns:
            PaywallDetectionResult with detection verdict
        """
        client = self._get_openai_client()
        if client is None:
            return PaywallDetectionResult(
                error="OpenAI client not available"
            )

        # Base64-encode the screenshot
        b64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
        media_type = f"image/{SCREENSHOT_TYPE}"

        # Build the prompt
        user_text = USER_PROMPT.format(
            url=url,
            content_length=content_length
        )

        try:
            response = await client.chat.completions.create(
                model=VISION_MODEL,
                max_tokens=VISION_MAX_TOKENS,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64_image}",
                                    "detail": VISION_DETAIL
                                }
                            }
                        ]
                    }
                ]
            )

            # Parse the response
            raw_text = response.choices[0].message.content.strip()

            # Clean up potential markdown fences
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(raw_text)

            result = PaywallDetectionResult(
                is_paywalled=parsed.get("is_paywalled", False),
                confidence=parsed.get("confidence", 0.0),
                paywall_type=parsed.get("paywall_type", "none"),
                description=parsed.get("description", ""),
            )

            fact_logger.logger.info(
                f"Visual paywall analysis: "
                f"paywalled={result.is_paywalled}, "
                f"confidence={result.confidence:.2f}, "
                f"type={result.paywall_type}"
            )

            return result

        except json.JSONDecodeError as e:
            fact_logger.logger.warning(
                f"Vision model returned invalid JSON: {e}"
            )
            return PaywallDetectionResult(
                error=f"Invalid JSON from vision model: {e}"
            )
        except Exception as e:
            fact_logger.logger.warning(
                f"Visual paywall detection failed: {type(e).__name__}: {e}"
            )
            return PaywallDetectionResult(
                error=f"Detection failed: {e}"
            )

    async def detect(
        self,
        page: Page,
        url: str,
        content_length: int,
    ) -> PaywallDetectionResult:
        """
        Full detection pipeline: screenshot + vision analysis.

        This is the main method to call from the scraper.

        Args:
            page: Active Playwright page (must still be open/navigated)
            url: The page URL
            content_length: Chars extracted so far

        Returns:
            PaywallDetectionResult
        """
        # Step 1: Take screenshot
        screenshot_bytes = await self.take_screenshot(page)
        if not screenshot_bytes:
            return PaywallDetectionResult(
                error="Failed to capture screenshot"
            )

        # Step 2: Analyze with vision model
        result = await self.analyze_screenshot(
            screenshot_bytes, url, content_length
        )

        return result
