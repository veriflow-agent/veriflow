# agents/fact_checker.py
"""
Fact Checker Agent - UPDATED WITH TIER FILTERING
Compares claimed facts against source excerpts

✅ TIER FILTERING: Only uses Tier 1 (0.85-1.0) and Tier 2 (0.70-0.84) sources
✅ TIER PRECEDENCE: Tier 1 sources override Tier 2 when there are contradictions
✅ SIMPLIFIED OUTPUT: Single comprehensive report field
"""

from langsmith import traceable
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import time

from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config
from utils.source_metadata import SourceMetadata


class FactCheckResult(BaseModel):
    """Result of fact checking - simplified with single report field"""
    fact_id: str
    statement: str
    match_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    report: str = Field(description="Comprehensive verification report")
    tier_breakdown: Optional[Dict[str, int]] = None


class FactChecker:
    """
    Checks facts against extracted excerpts

    ✅ TIER FILTERING:
    - Discards Tier 3+ sources (< 0.70 credibility)
    - Only evaluates against Tier 1 (0.85-1.0) and Tier 2 (0.70-0.84)
    - Sorts excerpts by tier (Tier 1 first) before evaluation
    """

    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        self.parser = JsonOutputParser(pydantic_object=FactCheckResult)

        # Load prompts
        from prompts.checker_prompts import get_checker_prompts
        self.prompts = get_checker_prompts()

        fact_logger.log_component_start("FactChecker", model="gpt-4o")

    @traceable(
        name="check_fact_accuracy",
        run_type="chain",
        tags=["fact-checking", "verification", "tier-filtering"]
    )
    async def check_fact(
        self, 
        fact, 
        excerpts: dict,
        source_metadata: Optional[Dict[str, SourceMetadata]] = None
    ) -> FactCheckResult:
        """
        Check a fact against source excerpts

        ✅ TIER FILTERING: Filters out Tier 3+ sources before evaluation
        ✅ TIER ORDERING: Presents Tier 1 sources first to the LLM

        Args:
            fact: Fact object with id and statement
            excerpts: Dict of URL -> list of excerpt dicts
            source_metadata: Optional dict of URL -> SourceMetadata for tier info
        """
        start_time = time.time()

        fact_logger.logger.info(
            f"🔍 Checking fact {fact.id}: {fact.statement[:50]}...",
            extra={"fact_id": fact.id}
        )

        # Filter and sort excerpts by tier
        filtered_excerpts = self._filter_by_tier(excerpts, source_metadata)

        if not filtered_excerpts:
            fact_logger.logger.warning(
                f"⚠️ No Tier 1/2 sources for {fact.id}",
                extra={"fact_id": fact.id}
            )
            return FactCheckResult(
                fact_id=fact.id,
                statement=fact.statement,
                match_score=0.0,
                confidence=0.0,
                report="Unable to verify - no credible Tier 1 or Tier 2 sources found. Web search did not return authoritative sources for this claim.",
                tier_breakdown={"tier1": 0, "tier2": 0, "filtered": len(excerpts)}
            )

        # Evaluate against filtered excerpts
        result = await self._evaluate_fact(fact, filtered_excerpts, source_metadata)

        duration = time.time() - start_time
        fact_logger.logger.info(
            f"✅ Fact {fact.id} checked: score={result.match_score:.2f}",
            extra={
                "fact_id": fact.id,
                "match_score": result.match_score,
                "duration_seconds": round(duration, 2)
            }
        )

        return result

    def _filter_by_tier(
        self, 
        excerpts: dict, 
        source_metadata: Optional[Dict[str, SourceMetadata]]
    ) -> list:
        """
        Filter excerpts to only include Tier 1 and Tier 2 sources
        Returns a flat list sorted by tier (Tier 1 first)
        """
        tier1_excerpts = []
        tier2_excerpts = []
        filtered_count = 0

        for url, url_excerpts in excerpts.items():
            # Get credibility score - handle both object and dict formats
            if source_metadata and url in source_metadata:
                meta = source_metadata[url]
                # Support both SourceMetadata objects and plain dicts
                if hasattr(meta, 'credibility_score'):
                    score = meta.credibility_score
                elif isinstance(meta, dict):
                    score = meta.get('credibility_score', 0.75)
                else:
                    score = 0.75
            else:
                score = 0.75  # Default to Tier 2 if unknown

            # Classify by tier
            if score >= 0.85:  # Tier 1
                for ex in url_excerpts:
                    tier1_excerpts.append({
                        **ex,
                        'url': url,
                        'tier': 1,
                        'credibility_score': score
                    })
            elif score >= 0.70:  # Tier 2
                for ex in url_excerpts:
                    tier2_excerpts.append({
                        **ex,
                        'url': url,
                        'tier': 2,
                        'credibility_score': score
                    })
            else:  # Tier 3+ - filtered out
                filtered_count += len(url_excerpts)

        if filtered_count > 0:
            fact_logger.logger.debug(
                f"🗑️ Filtered {filtered_count} Tier 3+ excerpts",
                extra={"filtered_count": filtered_count}
            )

        # Return Tier 1 first, then Tier 2
        return tier1_excerpts + tier2_excerpts

    def _format_excerpts(self, excerpts: list, source_metadata: Optional[Dict[str, SourceMetadata]] = None) -> str:
        """Format excerpts for the prompt, separated by tier"""
        if not excerpts:
            return "No credible source excerpts available."

        tier1_excerpts = [e for e in excerpts if e.get('tier') == 1]
        tier2_excerpts = [e for e in excerpts if e.get('tier') == 2]

        formatted = []

        # Format Tier 1 sources first
        if tier1_excerpts:
            formatted.append("=" * 60)
            formatted.append("TIER 1 SOURCES (HIGHEST AUTHORITY - TRUST THESE FIRST)")
            formatted.append("=" * 60)

            for ex in tier1_excerpts:
                url = ex['url']
                metadata = source_metadata.get(url) if source_metadata else None

                if metadata:
                    formatted.append(
                        f"\n[Source: {metadata.name} ({metadata.source_type})]\n"
                        f"Credibility: {metadata.credibility_tier} (Score: {metadata.credibility_score:.2f})\n"
                        f"Relevance: {ex['relevance']}\n"
                        f"Quote: {ex['quote']}\n"
                        f"URL: {url}\n"
                    )
                else:
                    formatted.append(
                        f"\n[Source: {url}]\n"
                        f"Tier: 1\n"
                        f"Relevance: {ex['relevance']}\n"
                        f"Quote: {ex['quote']}\n"
                    )

        # Format Tier 2 sources next
        if tier2_excerpts:
            formatted.append("\n" + "=" * 60)
            formatted.append("TIER 2 SOURCES (CREDIBLE - SECONDARY AUTHORITY)")
            formatted.append("=" * 60)

            for ex in tier2_excerpts:
                url = ex['url']
                metadata = source_metadata.get(url) if source_metadata else None

                if metadata:
                    formatted.append(
                        f"\n[Source: {metadata.name} ({metadata.source_type})]\n"
                        f"Credibility: {metadata.credibility_tier} (Score: {metadata.credibility_score:.2f})\n"
                        f"Relevance: {ex['relevance']}\n"
                        f"Quote: {ex['quote']}\n"
                        f"URL: {url}\n"
                    )
                else:
                    formatted.append(
                        f"\n[Source: {url}]\n"
                        f"Tier: 2\n"
                        f"Relevance: {ex['relevance']}\n"
                        f"Quote: {ex['quote']}\n"
                    )

        return "\n".join(formatted)

    @traceable(name="evaluate_fact_match", run_type="llm")
    async def _evaluate_fact(self, fact, excerpts: list, source_metadata: Optional[Dict[str, SourceMetadata]] = None) -> FactCheckResult:
        """
        Evaluate fact accuracy against excerpts
        ✅ Emphasizes tier precedence in prompt

        Args:
            fact: Fact object
            excerpts: list of excerpt dicts with url, quote, relevance, tier
            source_metadata: Source metadata for tier information
        """
        # Format excerpts with tier separation
        excerpts_text = self._format_excerpts(excerpts, source_metadata)

        # ✅ Enhanced system prompt with tier precedence
        tier_precedence_note = """

⚠️ CRITICAL: TIER 1 SOURCES TAKE ABSOLUTE PRECEDENCE

When evaluating facts:
1. Prioritize Tier 1 sources (0.85-1.0 credibility) as the PRIMARY TRUTH
2. Use Tier 2 sources (0.70-0.84 credibility) only for supporting context
3. If Tier 1 and Tier 2 contradict, ALWAYS trust Tier 1
4. If only Tier 2 sources available, note this limitation in your report

Examples: 
"While Tier 2 sources (Travel Blog) mention Chef Mario, Tier 1 sources (Official Restaurant Website, Michelin Guide) confirm Chef Julia is the current head chef. Tier 1 takes precedence."
"While Tier 2 source (political blog) mentions that the bill was passed, Tier 1 source (official government website) states it was rejected. Tier 1 is the final authority."
"""

        system_prompt = self.prompts["system"] + tier_precedence_note + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", self.prompts["user"] + "\n\n{format_instructions}\n\nReturn your response as valid JSON.")
        ])

        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"fact_checker_{fact.id}")

        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug(
            "🔗 Invoking LLM for fact checking",
            extra={"fact_id": fact.id, "num_excerpts": len(excerpts)}
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "excerpts": excerpts_text
            },
            config={"callbacks": callbacks.handlers}
        )

        # Calculate tier breakdown
        tier1_count = len([e for e in excerpts if e.get('tier') == 1])
        tier2_count = len([e for e in excerpts if e.get('tier') == 2])

        # Parse and return
        return FactCheckResult(
            fact_id=fact.id,
            statement=fact.statement,
            match_score=response['match_score'],
            confidence=response['confidence'],
            report=response['report'],
            tier_breakdown={"tier1": tier1_count, "tier2": tier2_count}
        )