# agents/fact_checker.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel
import time

class FactCheckResult(BaseModel):
    fact_id: str
    statement: str
    match_score: float
    assessment: str
    discrepancies: str
    confidence: float
    reasoning: str  # Added for transparency

class FactChecker:
    """Compare facts against source excerpts with LangSmith tracing"""

    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Stronger model for accuracy
            temperature=0
        )

        fact_logger.log_component_start("FactChecker", model="gpt-4o")

    @traceable(
        name="check_fact_accuracy",
        run_type="chain",
        tags=["fact-checking", "verification"]
    )
    async def check_fact(self, fact: Fact, excerpts: dict) -> FactCheckResult:
        """
        Compare fact against extracted excerpts with full tracing
        """
        start_time = time.time()

        # Compile all excerpts
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
    async def _evaluate_fact(self, fact: Fact, excerpts: list) -> FactCheckResult:
        """Evaluate fact accuracy against excerpts"""

        excerpts_text = "\n\n".join([
            f"[Source: {ex['url']}]\nRelevance: {ex['relevance']}\nQuote: {ex['quote']}"
            for ex in excerpts
        ])

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fact-checking expert with high standards for accuracy.

Compare the claimed fact with excerpts from sources.

SCORING CRITERIA:
1.0 - Perfect match: fact directly stated with same specifics
0.9 - Excellent match: very close, minor wording differences only
0.8 - Very good match: same core fact, slightly different details
0.7 - Good match: same general fact, some interpretation needed
0.6 - Acceptable match: mostly accurate but missing some context
0.5 - Partial match: contains some truth but incomplete/ambiguous
0.4 - Weak match: misleading or missing important qualifiers
0.3 - Poor match: significant discrepancies
0.2 - Very poor match: mostly inaccurate
0.1 - Nearly false: contradicted by sources
0.0 - False: completely contradicted or unsupported

Be precise. Note ANY discrepancies, missing context, or nuances.

Return JSON:
{
  "match_score": 0.95,
  "assessment": "detailed assessment of accuracy",
  "discrepancies": "any issues found, or 'none'",
  "confidence": 0.90,
  "reasoning": "step-by-step explanation of your scoring"
}"""),
            ("user", """CLAIMED FACT:
{fact}

SOURCE EXCERPTS:
{excerpts}

Evaluate the accuracy of this fact against the source excerpts.""")
        ])

        callbacks = langsmith_config.get_callbacks(f"fact_checker_{fact.id}")
        chain = prompt | self.llm

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "excerpts": excerpts_text
            },
            config={"callbacks": callbacks.handlers}
        )

        import json
        data = json.loads(response.content)

        return FactCheckResult(
            fact_id=fact.id,
            statement=fact.statement,
            match_score=data['match_score'],
            assessment=data['assessment'],
            discrepancies=data['discrepancies'],
            confidence=data['confidence'],
            reasoning=data['reasoning']
        )