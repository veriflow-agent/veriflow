# utils/source_metadata.py
"""
Source Metadata Utility
Manages source information for fact-checking with AI-powered name extraction
"""

from pydantic import BaseModel
from typing import Optional, Dict
from urllib.parse import urlparse
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import asyncio

from utils.logger import fact_logger


class SourceMetadata(BaseModel):
    """Metadata about a source used for fact-checking"""
    url: str
    name: str
    source_type: str
    credibility_score: float
    credibility_tier: str
    supports_claim: Optional[bool] = None
    key_excerpt: Optional[str] = None


class SourceNameExtractor:
    """Extract clean, human-readable names from page titles using AI"""

    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        self.parser = JsonOutputParser()

        # Cache for extracted names
        self.name_cache: Dict[str, str] = {}

        # Prompt for name extraction
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting clean publication names from web page titles.

Your job: Convert a raw page title into a clean, readable source name.

RULES:
1. Extract the main publication/organization name
2. Remove article titles, dates, navigation elements
3. Use proper capitalization and spacing
4. If it's clearly an official website, add "Official Website"
5. Be concise - aim for 2-5 words max

EXAMPLES:
Input: "New Chef Announced - Restaurant Del Mar - Official Site"
Output: {{"name": "Restaurant Del Mar Official Website", "type": "Official Website"}}

Input: "Travel & Leisure | Best Restaurants 2024 | Food"
Output: {{"name": "Travel & Leisure", "type": "Travel & Lifestyle Magazine"}}

Input: "Government of Canada - Health Canada - News Release"
Output: {{"name": "Health Canada", "type": "Government Agency"}}

Input: "Harvard Medical School - Research - Publications"
Output: {{"name": "Harvard Medical School", "type": "Academic Institution"}}

Input: "TechCrunch | Startup News"
Output: {{"name": "TechCrunch", "type": "Technology News"}}

Return ONLY valid JSON with 'name' and 'type' fields."""),
            ("user", "Extract clean source name from this page title:\n\nTitle: {title}\nURL: {url}\n\nReturn JSON only.")
        ])

    async def extract_name(self, url: str, title: str) -> tuple[str, str]:
        """
        Extract clean source name from page title

        Args:
            url: Source URL
            title: Page title

        Returns:
            Tuple of (clean_name, source_type)
        """
        # Check cache first
        cache_key = f"{url}::{title}"
        if cache_key in self.name_cache:
            cached = self.name_cache[cache_key]
            return cached.split(":::")

        try:
            # Use AI to extract clean name
            chain = self.prompt | self.llm | self.parser

            response = await chain.ainvoke({
                "title": title[:200],  # Limit title length
                "url": url
            })

            name = response.get('name', self._fallback_name(url))
            source_type = response.get('type', 'Website')

            # Cache result
            self.name_cache[cache_key] = f"{name}:::{source_type}"

            fact_logger.logger.debug(
                f"Extracted source name: {name}",
                extra={"url": url, "title": title[:100], "extracted_name": name}
            )

            return name, source_type

        except Exception as e:
            fact_logger.logger.warning(
                f"Name extraction failed, using fallback: {e}",
                extra={"url": url, "error": str(e)}
            )
            return self._fallback_name(url), "Website"

    def _fallback_name(self, url: str) -> str:
        """
        Fallback name extraction from domain

        Args:
            url: Source URL

        Returns:
            Cleaned domain name
        """
        try:
            domain = urlparse(url).netloc.lower()

            # Remove www.
            domain = domain.replace('www.', '')

            # Known domain mappings
            domain_map = {
                'nytimes.com': 'The New York Times',
                'washingtonpost.com': 'The Washington Post',
                'wsj.com': 'The Wall Street Journal',
                'reuters.com': 'Reuters',
                'bbc.com': 'BBC News',
                'bbc.co.uk': 'BBC',
                'cnn.com': 'CNN',
                'forbes.com': 'Forbes',
                'bloomberg.com': 'Bloomberg',
                'theguardian.com': 'The Guardian',
                'ft.com': 'Financial Times',
                'apnews.com': 'Associated Press',
                'nbcnews.com': 'NBC News',
                'cbsnews.com': 'CBS News',
                'abcnews.go.com': 'ABC News',
                'usatoday.com': 'USA Today',
                'latimes.com': 'Los Angeles Times',
                'chicagotribune.com': 'Chicago Tribune',
                'sfgate.com': 'San Francisco Chronicle',
                'time.com': 'TIME',
                'newsweek.com': 'Newsweek',
                'politico.com': 'Politico',
                'axios.com': 'Axios',
                'vox.com': 'Vox',
                'slate.com': 'Slate',
                'salon.com': 'Salon',
                'huffpost.com': 'HuffPost',
                'dailymail.co.uk': 'Daily Mail',
                'telegraph.co.uk': 'The Telegraph',
                'independent.co.uk': 'The Independent',
                'economist.com': 'The Economist',
                'newyorker.com': 'The New Yorker',
                'nationalgeographic.com': 'National Geographic',
                'scientificamerican.com': 'Scientific American',
                'nature.com': 'Nature',
                'science.org': 'Science',
                'nih.gov': 'National Institutes of Health',
                'cdc.gov': 'CDC',
                'who.int': 'World Health Organization',
                'unesco.org': 'UNESCO',
                'wikipedia.org': 'Wikipedia',
                'britannica.com': 'Encyclopedia Britannica',
            }

            if domain in domain_map:
                return domain_map[domain]

            # Generic cleanup for unknown domains
            # Remove TLD
            name = domain.rsplit('.', 1)[0]

            # Replace hyphens and underscores with spaces
            name = name.replace('-', ' ').replace('_', ' ')

            # Title case
            name = name.title()

            return name

        except Exception as e:
            fact_logger.logger.error(f"Fallback name extraction failed: {e}")
            return url[:50]  # Last resort


def create_source_metadata(
    url: str,
    name: str,
    source_type: str,
    credibility_score: float,
    credibility_tier: str
) -> SourceMetadata:
    """
    Convenience function to create SourceMetadata

    Args:
        url: Source URL
        name: Human-readable source name
        source_type: Type of source
        credibility_score: Credibility score (0.0-1.0)
        credibility_tier: Credibility tier string

    Returns:
        SourceMetadata object
    """
    return SourceMetadata(
        url=url,
        name=name,
        source_type=source_type,
        credibility_score=credibility_score,
        credibility_tier=credibility_tier
    )