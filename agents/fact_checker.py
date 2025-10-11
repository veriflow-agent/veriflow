# agents/fact_checker.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time

from prompts.checker_prompts import get_checker_prompts
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config
from utils.source_metadata import SourceMetadata

class FactCheckResult(BaseModel):
    fact_id: str
    statement: str
    match_score: float
    assessment: str
    discrepancies: str
    confidence: float
    reasoning: str
    sources_consulted: List[Dict[str, Any]] = []

class CheckerOutput(BaseModel):
    match_score: float = Field(description="Accuracy score from 0.0 to 1.0")
    assessment: str = Field(description="Detailed assessment of the fact")
    discrepancies: str = Field(description="Any discrepancies found")
    confidence: float = Field(description="Confidence in this evaluation")
    reasoning: str = Field(description="Step-by-step reasoning")

class FactChecker:
    """Compare facts against source excerpts with LangSmith tracing"""

    def __init__(self, config):
        self.config = config

        # ✅ PROPER JSON MODE - OpenAI guarantees valid JSON
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        # ✅ SIMPLE PARSER - No fixing needed
        self.parser = JsonOutputParser(pydantic_object=CheckerOutput)

        # Load prompts
        self.prompts = get_checker_prompts()

        fact_logger.log_component_start("FactChecker", model="gpt-4o")

    @traceable(
        name="check_fact_accuracy",
        run_type="chain",
        tags=["fact-checking", "verification"]
    )
    async def check_fact(
        self, 
        fact, 
        excerpts: dict,
        source_metadata: Optional[Dict[str, SourceMetadata]] = None # ✅ NEW parameter
    ) -> FactCheckResult:
        """
        Compare fact against extracted excerpts with full tracing

        Args:
            fact: Fact object with id, statement, sources
            excerpts: dict of {url: [excerpt_objects]}
        """
        start_time = time.time()

        # Compile all excerpts from all URLs into a single list
        all_excerpts = []
        for url, url_excerpts in excerpts.items():
            for excerpt in url_excerpts:
                all_excerpts.append({
                    "url": url,
                    "quote": excerpt['quote'],
                    "relevance": excerpt.get('relevance', 0.5)
                })

        fact_logger.logger.info(
            f"⚖️ Checking fact {fact.id}",
            extra={
                "fact_id": fact.id,
                "statement": fact.statement[:100],
                "num_excerpts": len(all_excerpts),
                "num_sources": len(excerpts)
            }
        )

        if not all_excerpts:
            fact_logger.logger.warning(
                f"⚠️ No excerpts found for fact {fact.id}",
                extra={"fact_id": fact.id}
            )
            return FactCheckResult(
                fact_id=fact.id,
                statement=fact.statement,
                match_score=0.0,
                assessment="No supporting excerpts found in sources",
                discrepancies="Cannot verify - no relevant content found",
                confidence=0.0,
                reasoning="No excerpts available for comparison"
            )

        try:
            result = await self._evaluate_fact(fact, all_excerpts, source_metadata)

            duration = time.time() - start_time
            fact_logger.log_component_complete(
                "FactChecker",
                duration,
                fact_id=fact.id,
                match_score=result.match_score,
                confidence=result.confidence
            )

            fact_logger.logger.info(
                f"📊 Fact check complete for {fact.id}: {result.match_score:.2f}",
                extra={
                    "fact_id": fact.id,
                    "match_score": result.match_score,
                    "confidence": result.confidence,
                    "assessment_summary": result.assessment[:100]
                }
            )

            return result

        except Exception as e:
            fact_logger.log_component_error("FactChecker", e, fact_id=fact.id)
            raise

    def _format_excerpts_with_sources(
        self, 
        excerpts: list, 
        source_metadata: Optional[Dict[str, SourceMetadata]]
    ) -> str:
        """
        Format excerpts with source attribution for the prompt

        Args:
            excerpts: list of excerpt dicts with 'url', 'quote', 'relevance'
            source_metadata: dict mapping URL to SourceMetadata

        Returns:
            Formatted string with source names included
        """
        if not excerpts:
            return "NO EXCERPTS FOUND - No relevant content located in source documents."

        formatted = []
        for ex in excerpts:
            url = ex['url']
            metadata = source_metadata.get(url) if source_metadata else None

            if metadata:
                source_name = metadata.name
                source_type = metadata.source_type
                credibility_tier = metadata.credibility_tier

                formatted.append(
                    f"[Source: {source_name} ({source_type})]\n"
                    f"Credibility: {credibility_tier}\n"
                    f"Relevance: {ex['relevance']}\n"
                    f"Quote: {ex['quote']}\n"
                    f"URL: {url}\n"
                )
            else:
                # Fallback if no metadata
                formatted.append(
                    f"[Source: {url}]\n"
                    f"Relevance: {ex['relevance']}\n"
                    f"Quote: {ex['quote']}\n"
                )

        return "\n\n".join(formatted)

    @traceable(name="evaluate_fact_match", run_type="llm")
    async def _evaluate_fact(self, fact, excerpts: list, source_metadata: Optional[Dict[str, SourceMetadata]] = None) -> FactCheckResult:
        """
        Evaluate fact accuracy against excerpts

        Args:
            fact: Fact object
            excerpts: list of excerpt dicts with url, quote, relevance
        """
        # Format excerpts into readable text for the prompt
        excerpts_text = self._format_excerpts(excerpts)

        # ✅ EXPLICIT JSON MENTION
        system_prompt = self.prompts["system"] + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", self.prompts["user"] + "\n\n{format_instructions}\n\nReturn your response as valid JSON.")
        ])

        # ✅ FORMAT INSTRUCTIONS
        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"fact_checker_{fact.id}")

        # ✅ CLEAN CHAIN - No manual JSON parsing needed
        chain = prompt_with_format | self.llm | self.parser

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "excerpts": excerpts_text
            },
            config={"callbacks": callbacks.handlers}
        )

        # ✅ NEW: Build sources_consulted from excerpts and metadata
        sources_consulted = []
        if source_metadata:
            for ex in excerpts:
                url = ex['url']
                metadata = source_metadata.get(url)
                if metadata:
                    # Determine if this source supports the claim based on relevance
                    supports = ex.get('relevance', 0.5) >= 0.7

                    sources_consulted.append({
                        "url": url,
                        "name": metadata.name,
                        "source_type": metadata.source_type,
                        "credibility_score": metadata.credibility_score,
                        "supports_claim": supports,
                        "key_excerpt": ex['quote'][:200] + "..." if len(ex['quote']) > 200 else ex['quote']
                    })

        # Remove duplicates (same URL might have multiple excerpts)
        seen_urls = set()
        unique_sources = []
        for source in sources_consulted:
            if source['url'] not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source['url'])

        # ✅ DIRECT DICT ACCESS - Parser returns clean dict
        return FactCheckResult(
            fact_id=fact.id,
            statement=fact.statement,
            match_score=response['match_score'],
            assessment=response['assessment'],
            discrepancies=response['discrepancies'],
            confidence=response['confidence'],
            reasoning=response['reasoning'],
            sources_consulted=unique_sources  # ✅ NEW
        )

    def _format_excerpts(self, excerpts: list) -> str:
        """
        Format excerpts list into readable text for the prompt

        Args:
            excerpts: list of dicts with 'url', 'quote', 'relevance'

        Returns:
            Formatted string for the prompt
        """
        if not excerpts:
            return "NO EXCERPTS FOUND - No relevant content located in source documents."

        formatted = []
        for ex in excerpts:
            formatted.append(
                f"[Source: {ex['url']}]\n"
                f"Relevance: {ex['relevance']}\n"
                f"Quote: {ex['quote']}\n"
            )

        return "\n\n".join(formatted)