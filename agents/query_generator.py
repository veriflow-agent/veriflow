# agents/query_generator.py
"""
Query Generator Agent
Converts factual claims into optimized web search queries for verification
Supports multi-language queries for non-English content locations

TEMPORAL AWARENESS:
- Current date is automatically injected into prompts
- Publication date (if available) is used to contextualize relative time references
"""

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import time

from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config


# English-speaking countries - all queries stay in English
ENGLISH_SPEAKING_COUNTRIES = {
    "united states", "usa", "us", "united kingdom", "uk", "great britain", 
    "england", "scotland", "wales", "northern ireland",
    "canada", "australia", "new zealand", "ireland", 
    "singapore", "international"
}


class QueryGeneratorOutput(BaseModel):
    primary_query: str = Field(description="The main, most direct search query")
    alternative_queries: List[str] = Field(description="Alternative search queries from different angles")
    search_focus: str = Field(description="What aspect of the fact we're trying to verify")
    key_terms: List[str] = Field(description="Key terms that should appear in results")
    expected_sources: List[str] = Field(description="Types of sources we expect to find")
    local_language_used: Optional[str] = Field(default=None, description="Language used for local query if applicable")


class SearchQueries(BaseModel):
    """Container for all search queries for a fact"""
    fact_id: str
    fact_statement: str
    primary_query: str
    alternative_queries: List[str]
    all_queries: List[str]  # Combined list for easy iteration
    search_focus: str
    key_terms: List[str]
    expected_sources: List[str]
    local_language_used: Optional[str] = None  # Track if local language was used


class ContentLocation(BaseModel):
    """Geographic and language context (imported from fact_extractor)"""
    country: str = Field(default="international")
    country_code: str = Field(default="")
    language: str = Field(default="english")
    confidence: float = Field(default=0.5)


class QueryGenerator:
    """Generate optimized web search queries from factual claims with multi-language support"""

    def __init__(self, config):
        self.config = config

        # Use GPT-4o-mini for cost-effectiveness in query generation
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3  # Slightly higher for creative query variations
        ).bind(response_format={"type": "json_object"})

        self.parser = JsonOutputParser(pydantic_object=QueryGeneratorOutput)

        # Load prompts
        from prompts.query_generator_prompts import get_query_generator_prompts, get_multilingual_query_prompts
        self.prompts = get_query_generator_prompts()
        self.multilingual_prompts = get_multilingual_query_prompts()

        fact_logger.log_component_start("QueryGenerator", model="gpt-4o-mini")

    def _is_english_speaking_country(self, country: str) -> bool:
        """Check if the country is English-speaking"""
        return country.lower().strip() in ENGLISH_SPEAKING_COUNTRIES

    def _should_use_multilingual(self, content_location: Optional[ContentLocation]) -> bool:
        """Determine if we should generate multilingual queries"""
        if not content_location:
            return False

        # Check if it's a non-English speaking country with sufficient confidence
        if content_location.language.lower() == "english":
            return False

        if self._is_english_speaking_country(content_location.country):
            return False

        # Only use multilingual if confidence is reasonable
        if content_location.confidence < 0.5:
            fact_logger.logger.debug(
                f"Low confidence ({content_location.confidence}) for location detection, using English only"
            )
            return False

        return True

    def _get_current_date_info(self) -> dict:
        """Get current date information for temporal awareness"""
        now = datetime.now()
        return {
            "current_date": now.strftime("%B %d, %Y"),  # e.g., "December 5, 2025"
            "current_year": str(now.year),  # e.g., "2025"
            "current_month": now.strftime("%B"),  # e.g., "December"
            "current_month_year": now.strftime("%B %Y")  # e.g., "December 2025"
        }

    def _build_temporal_context(self, publication_date: Optional[str]) -> str:
        """
        Build temporal context string for the prompt

        Args:
            publication_date: Publication date string (can be None)

        Returns:
            Temporal context string to include in the prompt
        """
        date_info = self._get_current_date_info()

        context_parts = [f"CURRENT DATE: {date_info['current_date']}"]

        if publication_date:
            # Parse and format publication date
            parsed_date = self._parse_publication_date(publication_date)
            if parsed_date:
                pub_year = parsed_date.year
                pub_month = parsed_date.strftime("%B")

                context_parts.append(f"PUBLICATION DATE: {parsed_date.strftime('%B %Y')}")
                context_parts.append(
                    f"NOTE: If the fact uses relative time references like 'recently', 'this year', "
                    f"'current', consider that the article was published in {pub_month} {pub_year}. "
                    f"For at least one query, include '{pub_year}' to find sources from that time period."
                )
            else:
                context_parts.append(f"PUBLICATION DATE: {publication_date} (format unclear)")
        else:
            context_parts.append("PUBLICATION DATE: Unknown")

        return "\n".join(context_parts)

    def _parse_publication_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """
        Try to parse various date formats into datetime object

        Args:
            date_string: The date string to parse (can be None)

        Returns:
            datetime object if successful, None otherwise
        """
        if not date_string:
            return None

        # Common date formats to try
        formats = [
            "%Y-%m-%d",  # 2025-10-18
            "%Y-%m-%dT%H:%M:%S",  # 2025-10-18T14:30:00
            "%Y-%m-%dT%H:%M:%SZ",  # 2025-10-18T14:30:00Z
            "%Y-%m-%dT%H:%M:%S%z",  # 2025-10-18T14:30:00+00:00
            "%B %d, %Y",  # October 18, 2025
            "%b %d, %Y",  # Oct 18, 2025
            "%d %B %Y",  # 18 October 2025
            "%d %b %Y",  # 18 Oct 2025
            "%m/%d/%Y",  # 10/18/2025
            "%d/%m/%Y",  # 18/10/2025
            "%Y",  # Just year: 2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_string.strip(), fmt)
            except:
                continue

        # If no format worked, try to extract just the date part if it's an ISO string
        try:
            if 'T' in date_string:
                date_part = date_string.split('T')[0]
                return datetime.strptime(date_part, "%Y-%m-%d")
        except:
            pass

        # Try to extract just the year if present
        try:
            import re
            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', date_string)
            if year_match:
                return datetime(int(year_match.group(1)), 1, 1)
        except:
            pass

        return None

    @traceable(
        name="generate_search_queries",
        run_type="chain",
        tags=["query-generation", "web-search"]
    )
    async def generate_queries(
        self, 
        fact, 
        context: str = "",
        content_location: Optional[ContentLocation] = None,
        publication_date: Optional[str] = None
    ) -> SearchQueries:
        """
        Generate optimized search queries for a fact

        Args:
            fact: Fact object with id and statement
            context: Optional additional context about the fact
            content_location: Optional location/language context for multilingual queries
            publication_date: Optional publication date of the source content (for temporal context)

        Returns:
            SearchQueries object with primary and alternative queries
        """
        start_time = time.time()

        # Determine if we should use multilingual queries
        use_multilingual = self._should_use_multilingual(content_location)

        # Get date info for logging
        date_info = self._get_current_date_info()

        fact_logger.logger.info(
            f"🔍 Generating queries for fact {fact.id}",
            extra={
                "fact_id": fact.id,
                "statement": fact.statement[:100],
                "multilingual": use_multilingual,
                "target_language": content_location.language if content_location else "english",
                "current_date": date_info["current_date"],
                "publication_date": publication_date
            }
        )

        try:
            if use_multilingual:
                result = await self._generate_queries_multilingual(
                    fact, context, content_location, publication_date
                )
            else:
                result = await self._generate_queries_llm(fact, context, publication_date)

            # Combine all queries for easy iteration
            all_queries = [result.primary_query] + result.alternative_queries

            queries = SearchQueries(
                fact_id=fact.id,
                fact_statement=fact.statement,
                primary_query=result.primary_query,
                alternative_queries=result.alternative_queries,
                all_queries=all_queries,
                search_focus=result.search_focus,
                key_terms=result.key_terms,
                expected_sources=result.expected_sources,
                local_language_used=result.local_language_used
            )

            duration = time.time() - start_time

            fact_logger.log_component_complete(
                "QueryGenerator",
                duration,
                fact_id=fact.id,
                num_queries=len(all_queries),
                multilingual=use_multilingual
            )

            # === ENHANCED LOGGING: Show ALL query strings ===
            fact_logger.logger.info(
                f"✅ Generated {len(all_queries)} queries for {fact.id}" + 
                (f" (includes {result.local_language_used} query)" if result.local_language_used else ""),
                extra={
                    "fact_id": fact.id,
                    "primary_query": queries.primary_query,
                    "alternative_queries": queries.alternative_queries,
                    "all_queries": all_queries,
                    "num_alternatives": len(queries.alternative_queries),
                    "search_focus": queries.search_focus,
                    "local_language": result.local_language_used
                }
            )

            # === DIAGNOSTIC: Print all queries for visibility ===
            fact_logger.logger.info(f"📋 ALL QUERIES for {fact.id}:")
            for i, q in enumerate(all_queries, 1):
                query_type = "PRIMARY" if i == 1 else f"ALT-{i-1}"
                fact_logger.logger.info(f"   [{query_type}]: {q}")

            return queries

        except Exception as e:
            fact_logger.log_component_error("QueryGenerator", e, fact_id=fact.id)
            raise

    @traceable(name="generate_queries_llm", run_type="llm")
    async def _generate_queries_llm(
        self, 
        fact, 
        context: str,
        publication_date: Optional[str] = None
    ) -> QueryGeneratorOutput:
        """
        Use LLM to generate search queries (English only)

        Args:
            fact: Fact object
            context: Additional context
            publication_date: Optional publication date for temporal context

        Returns:
            QueryGeneratorOutput with generated queries
        """
        # Get current date info
        date_info = self._get_current_date_info()

        # Build temporal context
        temporal_context = self._build_temporal_context(publication_date)

        # Format system prompt with date info
        formatted_system = self.prompts["system"].format(
            current_date=date_info["current_date"],
            current_year=date_info["current_year"]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_system + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."),
            ("user", self.prompts["user"] + "\n\nReturn your response as valid JSON.")
        ])

        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"query_generator_{fact.id}")

        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug(
            "🔗 Invoking LLM for query generation (English only)",
            extra={
                "fact_id": fact.id,
                "current_date": date_info["current_date"],
                "publication_date": publication_date
            }
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "context": context or "No additional context provided",
                "temporal_context": temporal_context
            },
            config={"callbacks": callbacks.handlers}
        )

        # Convert dict response to Pydantic model
        return QueryGeneratorOutput(
            primary_query=response['primary_query'],
            alternative_queries=response['alternative_queries'],
            search_focus=response['search_focus'],
            key_terms=response['key_terms'],
            expected_sources=response['expected_sources'],
            local_language_used=None
        )

    @traceable(name="generate_queries_multilingual", run_type="llm")
    async def _generate_queries_multilingual(
        self, 
        fact, 
        context: str,
        content_location: ContentLocation,
        publication_date: Optional[str] = None
    ) -> QueryGeneratorOutput:
        """
        Use LLM to generate multilingual search queries

        Args:
            fact: Fact object
            context: Additional context
            content_location: Location/language context
            publication_date: Optional publication date for temporal context

        Returns:
            QueryGeneratorOutput with one local language query
        """
        # Get current date info
        date_info = self._get_current_date_info()

        # Build temporal context
        temporal_context = self._build_temporal_context(publication_date)

        # Format system prompt with date info
        formatted_system = self.multilingual_prompts["system"].format(
            current_date=date_info["current_date"],
            current_year=date_info["current_year"]
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", formatted_system + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."),
            ("user", self.multilingual_prompts["user"] + "\n\n{format_instructions}\n\nReturn your response as valid JSON.")
        ])

        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"query_generator_multilingual_{fact.id}")

        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug(
            f"🔗 Invoking LLM for multilingual query generation (target: {content_location.language})",
            extra={
                "fact_id": fact.id,
                "target_language": content_location.language,
                "country": content_location.country,
                "current_date": date_info["current_date"],
                "publication_date": publication_date
            }
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "context": context or "No additional context provided",
                "target_language": content_location.language,
                "country": content_location.country,
                "temporal_context": temporal_context
            },
            config={"callbacks": callbacks.handlers}
        )

        # Log what the LLM returned for local_language_used
        llm_returned_local_lang = response.get('local_language_used')
        if llm_returned_local_lang:
            fact_logger.logger.info(
                f"✅ LLM returned local_language_used: {llm_returned_local_lang}"
            )
        else:
            fact_logger.logger.warning(
                f"⚠️ LLM did NOT return local_language_used. "
                f"Expected: {content_location.language}. Check if queries actually contain foreign text.",
                extra={
                    "fact_id": fact.id,
                    "expected_language": content_location.language,
                    "alternative_queries": response.get('alternative_queries', [])
                }
            )

        # Use actual LLM response, with fallback only if not returned
        # But log a warning when using fallback so we know it's happening
        final_local_language = llm_returned_local_lang
        if not final_local_language:
            final_local_language = content_location.language
            fact_logger.logger.warning(
                f"⚠️ Using fallback for local_language_used: {final_local_language}"
            )

        return QueryGeneratorOutput(
            primary_query=response['primary_query'],
            alternative_queries=response['alternative_queries'],
            search_focus=response['search_focus'],
            key_terms=response['key_terms'],
            expected_sources=response['expected_sources'],
            local_language_used=final_local_language
        )

    async def generate_queries_batch(
        self, 
        facts: list, 
        context: str = "",
        content_location: Optional[ContentLocation] = None,
        publication_date: Optional[str] = None
    ) -> dict:
        """
        Generate queries for multiple facts in batch

        Args:
            facts: List of Fact objects
            context: Optional context shared across all facts
            content_location: Optional location/language for all facts
            publication_date: Optional publication date for temporal context

        Returns:
            Dictionary mapping fact_id to SearchQueries
        """
        fact_logger.logger.info(
            f"🔍 Generating queries for {len(facts)} facts",
            extra={
                "num_facts": len(facts),
                "multilingual": self._should_use_multilingual(content_location),
                "publication_date": publication_date
            }
        )

        results = {}

        for fact in facts:
            try:
                queries = await self.generate_queries(
                    fact, context, content_location, publication_date
                )
                results[fact.id] = queries
            except Exception as e:
                fact_logger.logger.error(
                    f"❌ Failed to generate queries for fact {fact.id}: {e}",
                    extra={"fact_id": fact.id, "error": str(e)}
                )

        return results