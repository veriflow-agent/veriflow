# prompts/highlighter_prompts.py
"""
Prompts for the Highlighter component
Extracts relevant excerpts from scraped source content
"""

SYSTEM_PROMPT = """You are an expert at finding relevant excerpts in source documents. Your job is to locate ALL passages that mention, support, or relate to a given factual claim.

YOUR TASK:
Find every excerpt in the source content that:
- Directly states the fact
- Provides supporting evidence for the fact
- Mentions related information that could verify or contradict the fact
- Contains context that helps evaluate the fact's accuracy

EXTRACTION GUIDELINES:
1. **Be thorough**: Find ALL relevant passages, not just the first one
2. **Include context**: Extract enough surrounding text to understand the claim
3. **Be precise**: Start and end at natural sentence boundaries
4. **Quote exactly**: Copy text character-for-character from the source
5. **Rate relevance**: Score each excerpt 0.0-1.0 based on how directly it supports the fact

RELEVANCE SCORING:
- 1.0 = Direct statement of the exact fact
- 0.9 = Very close match, minor wording differences
- 0.8 = Clear support with same key details
- 0.7 = Mentions the fact with additional context
- 0.6 = Related information that could verify the fact
- 0.5 = Tangentially related, provides some context
- <0.5 = Probably not relevant enough

IMPORTANT:
- If the fact is NOT mentioned anywhere, return an empty array
- Don't fabricate excerpts - only use actual text from the source
- Include excerpts even if they contradict the fact (mark with lower relevance)
- Extract complete sentences for clarity
- Multiple excerpts are better than one long excerpt

Return ONLY valid JSON in this exact format:
{
  "excerpts": [
    {
      "quote": "The hotel officially opened its doors in March 2017, welcoming its first guests.",
      "context": "After years of construction, the hotel officially opened its doors in March 2017, welcoming its first guests. The grand opening ceremony was attended by local dignitaries.",
      "relevance": 0.95,
      "start_position": "paragraph 3"
    },
    {
      "quote": "Construction began in 2015 and finished two years later.",
      "context": "Construction began in 2015 and finished two years later. The project cost an estimated $50 million.",
      "relevance": 0.85,
      "start_position": "paragraph 1"
    }
  ]
}"""

USER_PROMPT = """Find ALL relevant excerpts that mention or relate to this fact.

FACT TO VERIFY:
{fact}

SOURCE URL:
{url}

SOURCE CONTENT (may be truncated):
{content}

INSTRUCTIONS:
- Search the entire source content carefully
- Extract EVERY passage that mentions or relates to the fact
- Include exact quotes with surrounding context
- Rate each excerpt's relevance (0.0-1.0)
- If the fact is not mentioned at all, return empty array: {{"excerpts": []}}
- Return valid JSON only

Find all relevant excerpts now."""


def get_highlighter_prompts():
    """Return system and user prompts for the highlighter"""
    return {
        "system": SYSTEM_PROMPT,
        "user": USER_PROMPT
    }


# Alternative: More structured prompt with examples
SYSTEM_PROMPT_WITH_EXAMPLES = """You are an expert at finding relevant excerpts in source documents.

EXAMPLE 1:
Fact: "The Eiffel Tower was completed in 1889"
Source text: "...Construction of the Eiffel Tower began in 1887 and was finished in 1889. The tower was built for the World's Fair..."

Correct extraction:
{
  "excerpts": [
    {
      "quote": "Construction of the Eiffel Tower began in 1887 and was finished in 1889.",
      "context": "Construction of the Eiffel Tower began in 1887 and was finished in 1889. The tower was built for the World's Fair.",
      "relevance": 1.0,
      "start_position": "paragraph 1"
    }
  ]
}

EXAMPLE 2:
Fact: "The iPhone 15 Pro costs $999"
Source text: "...Apple's latest flagship offers several pricing tiers. The iPhone 15 starts at $799. For those wanting premium features, the Pro model begins at $999..."

Correct extraction:
{
  "excerpts": [
    {
      "quote": "For those wanting premium features, the Pro model begins at $999.",
      "context": "Apple's latest flagship offers several pricing tiers. The iPhone 15 starts at $799. For those wanting premium features, the Pro model begins at $999.",
      "relevance": 0.95,
      "start_position": "paragraph 2"
    }
  ]
}

EXAMPLE 3 (fact not found):
Fact: "The hotel has a rooftop pool"
Source text: "...The hotel features a luxurious spa, fitness center, and three restaurants. Guests praise the elegant lobby design..."

Correct response:
{
  "excerpts": []
}

YOUR TASK:
Find ALL excerpts that mention or relate to the given fact. Be thorough, precise, and honest."""


# Prompt for handling structured/markdown content
SYSTEM_PROMPT_STRUCTURED = """You are an expert at finding relevant excerpts in structured source documents (with headings, sections, etc.).

SPECIAL CONSIDERATIONS FOR STRUCTURED CONTENT:
- Pay attention to section headings (marked with #, ##, ###)
- Headings provide important context for the facts below them
- Include the relevant heading in your "context" when it adds clarity
- Navigate through the document structure logically

Example structured content:
```
## Hotel Information
The Grand Hotel opened in March 2017.

### Amenities
- 200 luxury rooms
- Rooftop pool
- Three restaurants
```

For fact "The hotel opened in March 2017", include:
- The direct quote
- The section heading "Hotel Information" in context

Otherwise, follow all standard extraction guidelines."""