# agents/analyser.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List
import time
import json
from prompts.analyzer_prompts import get_analyzer_prompts
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config

class Fact(BaseModel):
    id: str
    statement: str
    sources: List[str]
    original_text: str
    confidence: float

class FactList(BaseModel):
    """List of extracted facts"""
    facts: List[dict] = Field(description="List of factual claims extracted from text")

class FactAnalyzer:
    """Extract factual claims with LangSmith tracing"""

    def __init__(self, config):
        self.config = config

        # Create base LLM WITHOUT model_kwargs for JSON
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )

        # Use with_structured_output for proper JSON handling
        self.structured_llm = self.llm.with_structured_output(
            FactList,
            method="json_mode"
        )

        # Load prompts during initialization
        self.prompts = get_analyzer_prompts()

        fact_logger.log_component_start("FactAnalyzer", model="gpt-4o-mini")

    @traceable(
        name="analyze_facts",
        run_type="chain",
        tags=["fact-extraction", "analyzer"]
    )
    async def analyze(self, parsed_content: dict) -> List[Fact]:
        """
        Extract facts with full LangSmith tracing
        """
        start_time = time.time()

        fact_logger.logger.info(
            "🔍 Starting fact analysis",
            extra={
                "text_length": len(parsed_content['text']),
                "num_sources": len(parsed_content['links']),
                "format": parsed_content.get('format', 'unknown')
            }
        )

        try:
            # Create prompt that explicitly asks for JSON
            system_prompt = self.prompts["system"] + "\n\nIMPORTANT: Return ONLY valid JSON with the exact structure shown. No markdown, no code blocks."

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", self.prompts["user"])
            ])

            # Get callbacks for LangSmith (safe to call)
            callbacks = langsmith_config.get_callbacks("fact_analyzer")

            # Create chain with structured output
            chain = prompt | self.structured_llm

            fact_logger.logger.debug("🔗 Invoking LangChain with structured output")

            # Safe callback usage
            config = {}
            if callbacks and hasattr(callbacks, 'handlers'):
                config = {"callbacks": callbacks.handlers}

            result = await chain.ainvoke(
                {
                    "text": parsed_content['text'],
                    "sources": self._format_sources(parsed_content['links'])
                },
                config=config
            )

            # result is now a FactList Pydantic object
            facts_data = result.facts if hasattr(result, 'facts') else result.get('facts', [])

            # Convert to Fact objects
            facts = []
            for i, fact_data in enumerate(facts_data):
                # Handle both dict and object formats
                if isinstance(fact_data, dict):
                    statement = fact_data.get('statement', '')
                    sources = fact_data.get('sources', [])
                    original_text = fact_data.get('original_text', '')
                    confidence = fact_data.get('confidence', 1.0)
                else:
                    statement = fact_data.statement
                    sources = fact_data.sources
                    original_text = fact_data.original_text
                    confidence = fact_data.confidence

                fact = Fact(
                    id=f"fact{i+1}",
                    statement=statement,
                    sources=sources,
                    original_text=original_text,
                    confidence=confidence
                )
                facts.append(fact)

                fact_logger.logger.debug(
                    f"📝 Extracted fact {fact.id}",
                    extra={
                        "fact_id": fact.id,
                        "statement": fact.statement[:100],
                        "num_sources": len(fact.sources)
                    }
                )

            duration = time.time() - start_time
            fact_logger.log_component_complete(
                "FactAnalyzer",
                duration,
                num_facts=len(facts),
                avg_sources_per_fact=sum(len(f.sources) for f in facts) / len(facts) if facts else 0
            )

            return facts

        except Exception as e:
            fact_logger.log_component_error("FactAnalyzer", e)

            # Log the full error for debugging
            fact_logger.logger.error(
                f"Full error details: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "text_preview": parsed_content['text'][:200]
                }
            )
            raise

    def _format_sources(self, links: List[dict]) -> str:
        """Format source links for the prompt"""
        if not links:
            return "No sources provided"
        return "\n".join([f"- {link['url']}" for link in links])