# agents/lie_detector.py - PARSING FIX
"""
This file shows the changes needed to fix JSON parsing errors in lie_detector.py

The problem: Claude sometimes returns JSON wrapped in markdown code fences like:
```json
{ ... }
```

Or with preamble text like "Here's my analysis:"

The fix: Add a cleaning function and use it before parsing.
"""

import re
import json

# ============================================
# ADD THIS HELPER FUNCTION (near the top of the file, after imports)
# ============================================

def clean_json_response(text: str) -> str:
    """
    Clean LLM response to extract pure JSON.
    Handles markdown code fences and preamble text.
    """
    if not text:
        return text

    # Remove markdown code fences
    # Pattern matches ```json ... ``` or ``` ... ```
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(code_block_pattern, text)
    if match:
        text = match.group(1)

    # Remove any text before the first { or [
    first_brace = text.find('{')
    first_bracket = text.find('[')

    if first_brace != -1 and first_bracket != -1:
        start = min(first_brace, first_bracket)
    elif first_brace != -1:
        start = first_brace
    elif first_bracket != -1:
        start = first_bracket
    else:
        return text  # No JSON structure found

    # Find the matching closing brace/bracket
    if text[start] == '{':
        # Find last }
        last_close = text.rfind('}')
        if last_close != -1:
            text = text[start:last_close + 1]
    else:
        # Find last ]
        last_close = text.rfind(']')
        if last_close != -1:
            text = text[start:last_close + 1]

    return text.strip()


# ============================================
# MODIFY THE analyze() METHOD - Replace the try/except block
# ============================================

# BEFORE (problematic code):
"""
try:
    response = await chain.ainvoke(
        {
            "current_date": current_date_str,
            "temporal_context": temporal_context,
            "article_source": article_source,
            "text": text
        },
        config={"callbacks": callbacks.handlers}
    )

    fact_logger.logger.info("✅ Lie detection analysis completed")

    return LieDetectionResult(**response)
"""

# AFTER (fixed code):
"""
try:
    # Get raw response from Claude (without the parser in the chain)
    prompt_chain = prompt_with_format | self.claude_llm

    raw_response = await prompt_chain.ainvoke(
        {
            "current_date": current_date_str,
            "temporal_context": temporal_context,
            "article_source": article_source,
            "text": text
        },
        config={"callbacks": callbacks.handlers}
    )

    # Extract content from AIMessage
    if hasattr(raw_response, 'content'):
        response_text = raw_response.content
    else:
        response_text = str(raw_response)

    # Clean the JSON response
    cleaned_json = clean_json_response(response_text)

    # Parse the cleaned JSON
    try:
        response = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        fact_logger.logger.error(f"JSON parsing failed: {e}")
        fact_logger.logger.error(f"Raw response: {response_text[:500]}...")
        raise ValueError(f"Invalid JSON response: {e}")

    fact_logger.logger.info("✅ Lie detection analysis completed")

    return LieDetectionResult(**response)
"""


# ============================================
# FULL UPDATED analyze() METHOD
# ============================================

async def analyze_FIXED(
    self, 
    text: str,
    url: Optional[str] = None,
    publication_date: Optional[str] = None
) -> "LieDetectionResult":
    """
    Analyze text for deception markers - FIXED VERSION

    Args:
        text: The article text to analyze
        url: Optional article URL
        publication_date: Optional publication date (if available)

    Returns:
        LieDetectionResult with comprehensive analysis
    """
    from utils.logger import fact_logger
    from utils.langsmith_config import langsmith_config
    from datetime import datetime

    fact_logger.logger.info("🔍 Starting lie detection analysis")

    # Limit content to avoid token limits
    if len(text) > 20000:
        fact_logger.logger.info("⚠️ Content too long, truncating to 20000 characters")
        text = text[:20000]

    # Get current date
    current_date = datetime.now()
    current_date_str = current_date.strftime("%B %d, %Y")

    # Build temporal context
    temporal_context = self._build_temporal_context(publication_date, current_date)

    # Build article source context
    article_source = f"ARTICLE URL: {url}" if url else "ARTICLE SOURCE: Plain text input"

    # Create prompt with system prompt that includes current date
    system_prompt = self.prompts["system"].format(current_date=current_date_str)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nCRITICAL: Return ONLY valid JSON. No markdown, no explanations, just the JSON object."),
        ("user", self.prompts["user"] + "\n\nReturn ONLY the JSON object, nothing else.")
    ])

    prompt_with_format = prompt.partial(
        format_instructions=self.parser.get_format_instructions()
    )

    callbacks = langsmith_config.get_callbacks("lie_detector_claude")

    # NOTE: Don't include parser in chain - we'll parse manually after cleaning
    prompt_chain = prompt_with_format | self.claude_llm

    try:
        # Get raw response
        raw_response = await prompt_chain.ainvoke(
            {
                "current_date": current_date_str,
                "temporal_context": temporal_context,
                "article_source": article_source,
                "text": text
            },
            config={"callbacks": callbacks.handlers}
        )

        # Extract content from AIMessage
        if hasattr(raw_response, 'content'):
            response_text = raw_response.content
        else:
            response_text = str(raw_response)

        fact_logger.logger.debug(f"Raw response length: {len(response_text)}")

        # Clean the JSON response (remove markdown fences, preamble, etc.)
        cleaned_json = clean_json_response(response_text)

        # Parse the cleaned JSON
        try:
            response = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            fact_logger.logger.error(f"JSON parsing failed after cleaning: {e}")
            fact_logger.logger.error(f"Cleaned JSON (first 500 chars): {cleaned_json[:500]}...")
            raise ValueError(f"Invalid JSON response from model: {e}")

        fact_logger.logger.info("✅ Lie detection analysis completed")

        return LieDetectionResult(**response)

    except Exception as e:
        fact_logger.logger.error(f"❌ Lie detection analysis failed: {e}")
        # Return a fallback result
        return LieDetectionResult(
            risk_level="UNKNOWN",
            credibility_score=50,
            markers_detected=[],
            positive_indicators=["Analysis incomplete due to error"],
            overall_assessment=f"Analysis failed: {str(e)}",
            conclusion="Unable to complete analysis",
            reasoning=f"Error occurred: {str(e)}"
        )