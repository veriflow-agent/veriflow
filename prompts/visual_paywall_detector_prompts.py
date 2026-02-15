# prompts/visual_paywall_detector_prompts.py
"""
Prompts for visual paywall detection using GPT-4o-mini vision.

When scraped content seems too short, we take a full-page screenshot
and ask a vision model to determine if a paywall, subscription gate,
registration wall, or content truncation is visible.
"""


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are a web page analyst specializing in detecting paywalls and access restrictions.

You will be shown a full-page screenshot of a news or media website.

Your job is to determine whether the page is blocking access to the full article content through ANY of the following mechanisms:

## PAYWALL INDICATORS TO LOOK FOR

### Visual Barriers
- Blurred, faded, or gradient-obscured text (article text becomes unreadable partway through)
- Overlay modals or popups asking to subscribe or log in
- Inline banners breaking the article flow with subscription CTAs
- "Content preview" areas where text cuts off abruptly

### Textual Indicators
- "Subscribe to continue reading"
- "Sign in to read the full article"
- "This article is for subscribers only"
- "Already a subscriber? Log in"
- "Start your free trial"
- "Get digital access"
- "Become a member"
- Pricing/plan information (monthly/yearly rates)
- "X free articles remaining"
- Registration forms embedded in the article

### Structural Indicators
- Article that appears to end abruptly after 1-2 paragraphs
- Large empty space where article content should be
- "Read more" locked behind a login/subscribe button
- Footer/navigation visible but article body is minimal

### NOT a Paywall (false positives to avoid)
- Newsletter signup forms at the END of a complete article
- "Share this article" buttons
- Related articles sections
- Cookie consent banners (these don't block content)
- Normal short articles (opinion pieces, breaking news briefs)

## RESPONSE FORMAT
Respond with ONLY a JSON object, no markdown backticks, no preamble:

{
    "is_paywalled": true/false,
    "confidence": 0.0-1.0,
    "paywall_type": "hard|soft|metered|registration|none",
    "description": "Brief explanation of what you see"
}

Where:
- "hard": Content is not delivered at all, only a teaser/summary shown
- "soft": Content is in the page but hidden by overlay/blur/CSS
- "metered": User has hit article limit ("X articles remaining")
- "registration": Free but requires account creation to read
- "none": No paywall detected"""


# ============================================================================
# USER PROMPT
# ============================================================================

USER_PROMPT = """Analyze this full-page screenshot of a web article.

URL: {url}
Extracted text length: {content_length} characters (seems short for a full article)

Is this page showing a paywall, subscription wall, or other access restriction that prevents reading the full article?

Respond with ONLY a JSON object."""
