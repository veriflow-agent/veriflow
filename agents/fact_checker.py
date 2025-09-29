# agents/fact_checker.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel, Field
import time
from typing import Dict, List
from prompts.checker_prompts import get_checker_prompts
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config

class FactCheckResult(BaseModel):
    fact_id: str
    statement: str
    match_score: float
    assessment: str
    discrepancies: str
    confidence: float
    reasoning: str

class CheckerOutput(BaseModel):
    """Structured output for fact checking"""
    match_score: float = Field(description="Match score between 0.0 and 1.0")
    assessment: str = Field(description="Assessment of the fact's accuracy")
    discrepancies: str = Field(description="Any discrepancies found or 'none'")
    confidence: float = Field(description="Confidence in this evaluation between 0.0 and 1.0")
    reasoning: str = Field(description="Step-by-step reasoning for the evaluation")

class FactChecker:
    """Compare facts against source excerpts with LangSmith tracing"""

    def __init__(self, config):
        self.config = config

        # Create base LLM
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Stronger model for accuracy
            temperature=0.1
        )

        # Use with_structured_output for proper JSON handling
        self.structured_llm = self.llm.with_structured_output(
            CheckerOutput,
            method="json_mode"
        )

        # Load prompts
        self.prompts = get_checker_prompts()

        fact_logger.log_component_start("FactChecker", model="gpt-4o")

    @traceable(
        name="check_fact_accuracy",
        run_type="chain",
        tags=["fact-checking", "verification"]
    )
    async def check_fact(self, fact, excerpts: dict) -> FactCheckResult:
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
            result = await self._evaluate_fact(fact, all_excerpts)

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

    @traceable(name="evaluate_fact_match", run_type="llm")
    async def _evaluate_fact(self, fact, excerpts: list) -> FactCheckResult:
        """
        Evaluate fact accuracy against excerpts

        Args:
            fact: Fact object
            excerpts: list of excerpt dicts with url, quote, relevance
        """
        # Format excerpts into readable text for the prompt
        excerpts_text = self._format_excerpts(excerpts)

        # Create prompt with explicit JSON instruction
        system_prompt = self.prompts["system"] + "\n\nIMPORTANT: Return ONLY valid JSON with the exact structure shown. No markdown, no code blocks."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", self.prompts["user"])
        ])

        callbacks = langsmith_config.get_callbacks(f"fact_checker_{fact.id}")

        # Create chain with structured output
        chain = prompt | self.structured_llm

        config = {}
        if callbacks and hasattr(callbacks, 'handlers'):
            config = {"callbacks": callbacks.handlers}

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "excerpts": excerpts_text
            },
            config=config
        )

        # response is now a CheckerOutput Pydantic object
        return FactCheckResult(
            fact_id=fact.id,
            statement=fact.statement,
            match_score=response.match_score,
            assessment=response.assessment,
            discrepancies=response.discrepancies,
            confidence=response.confidence,
            reasoning=response.reasoning
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