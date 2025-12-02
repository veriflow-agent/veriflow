# agents/query_generator.py
"""
Query Generator Agent
Converts factual claims into optimized web search queries for verification
Supports multi-language queries for non-English content locations
"""

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Optional
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

    @traceable(
        name="generate_search_queries",
        run_type="chain",
        tags=["query-generation", "web-search"]
    )
    async def generate_queries(
        self, 
        fact, 
        context: str = "",
        content_location: Optional[ContentLocation] = None
    ) -> SearchQueries:
        """
        Generate optimized search queries for a fact

        Args:
            fact: Fact object with id and statement
            context: Optional additional context about the fact
            content_location: Optional location/language context for multilingual queries

        Returns:
            SearchQueries object with primary and alternative queries
        """
        start_time = time.time()

        # Determine if we should use multilingual queries
        use_multilingual = self._should_use_multilingual(content_location)

        fact_logger.logger.info(
            f"🔍 Generating queries for fact {fact.id}",
            extra={
                "fact_id": fact.id,
                "statement": fact.statement[:100],
                "multilingual": use_multilingual,
                "target_language": content_location.language if content_location else "english"
            }
        )

        try:
            if use_multilingual:
                result = await self._generate_queries_multilingual(fact, context, content_location)
            else:
                result = await self._generate_queries_llm(fact, context)

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

            fact_logger.logger.info(
                f"✅ Generated {len(all_queries)} queries for {fact.id}" + 
                (f" (includes {result.local_language_used} query)" if result.local_language_used else ""),
                extra={
                    "fact_id": fact.id,
                    "primary_query": queries.primary_query,
                    "num_alternatives": len(queries.alternative_queries),
                    "search_focus": queries.search_focus,
                    "local_language": result.local_language_used
                }
            )

            return queries

        except Exception as e:
            fact_logger.log_component_error("QueryGenerator", e, fact_id=fact.id)
            raise

    @traceable(name="generate_queries_llm", run_type="llm")
    async def _generate_queries_llm(self, fact, context: str) -> QueryGeneratorOutput:
        """
        Use LLM to generate search queries (English only)

        Args:
            fact: Fact object
            context: Additional context

        Returns:
            QueryGeneratorOutput with generated queries
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts["system"] + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."),
            ("user", self.prompts["user"] + "\n\n{format_instructions}\n\nReturn your response as valid JSON.")
        ])

        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"query_generator_{fact.id}")

        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug(
            "🔗 Invoking LLM for query generation (English only)",
            extra={"fact_id": fact.id}
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "context": context or "No additional context provided"
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
        content_location: ContentLocation
    ) -> QueryGeneratorOutput:
        """
        Use LLM to generate multilingual search queries

        Args:
            fact: Fact object
            context: Additional context
            content_location: Location/language context

        Returns:
            QueryGeneratorOutput with one local language query
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.multilingual_prompts["system"] + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."),
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
                "country": content_location.country
            }
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "context": context or "No additional context provided",
                "target_language": content_location.language,
                "country": content_location.country
            },
            config={"callbacks": callbacks.handlers}
        )

        return QueryGeneratorOutput(
            primary_query=response['primary_query'],
            alternative_queries=response['alternative_queries'],
            search_focus=response['search_focus'],
            key_terms=response['key_terms'],
            expected_sources=response['expected_sources'],
            local_language_used=response.get('local_language_used', content_location.language)
        )

    async def generate_queries_batch(
        self, 
        facts: list, 
        context: str = "",
        content_location: Optional[ContentLocation] = None
    ) -> dict:
        """
        Generate queries for multiple facts in batch

        Args:
            facts: List of Fact objects
            context: Optional context shared across all facts
            content_location: Optional location/language for all facts

        Returns:
            Dictionary mapping fact_id to SearchQueries
        """
        fact_logger.logger.info(
            f"🔍 Generating queries for {len(facts)} facts",
            extra={
                "num_facts": len(facts),
                "multilingual": self._should_use_multilingual(content_location)
            }
        )

        results = {}

        for fact in facts:
            try:
                queries = await self.generate_queries(fact, context, content_location)
                results[fact.id] = queries
            except Exception as e:
                fact_logger.logger.error(
                    f"❌ Failed to generate queries for {fact.id}: {e}",
                    extra={"fact_id": fact.id, "error": str(e)}
                )
                # Create fallback query using just the fact statement
                results[fact.id] = SearchQueries(
                    fact_id=fact.id,
                    fact_statement=fact.statement,
                    primary_query=fact.statement[:100],  # Use fact as query
                    alternative_queries=[],
                    all_queries=[fact.statement[:100]],
                    search_focus="Direct fact verification",
                    key_terms=[],
                    expected_sources=[],
                    local_language_used=None
                )

        fact_logger.logger.info(
            f"✅ Query generation complete for {len(results)}/{len(facts)} facts",
            extra={
                "successful": len(results),
                "total": len(facts)
            }
        )

        return results