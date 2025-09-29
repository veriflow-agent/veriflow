# agents/analyzer.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List
import time

class Fact(BaseModel):
    id: str
    statement: str
    sources: List[str]
    original_text: str
    confidence: float

class FactAnalyzer:
    """Extract factual claims with LangSmith tracing"""

    def __init__(self, config):
        self.config = config
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

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
            prompt = ChatPromptTemplate.from_messages([
                ("system", self._get_system_prompt()),
                ("user", self._get_user_prompt())
            ])

            # Get callbacks for LangSmith
            callbacks = langsmith_config.get_callbacks("fact_analyzer")

            # Create chain with tracing
            chain = prompt | self.llm

            fact_logger.logger.debug("🔗 Invoking LangChain with callbacks")

            result = await chain.ainvoke(
                {
                    "text": parsed_content['text'],
                    "sources": self._format_sources(parsed_content['links'])
                },
                config={"callbacks": callbacks.handlers}
            )

            # Parse result
            import json
            facts_data = json.loads(result.content)

            # Convert to Fact objects
            facts = []
            for i, fact_data in enumerate(facts_data.get('facts', [])):
                fact = Fact(
                    id=f"fact{i+1}",
                    statement=fact_data['statement'],
                    sources=fact_data['sources'],
                    original_text=fact_data.get('original_text', ''),
                    confidence=fact_data.get('confidence', 1.0)
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
            raise

    def _get_system_prompt(self) -> str:
        return """You are a fact extraction expert. 
        Extract all factual claims from the provided text.

        For each fact, identify:
        1. The specific factual statement (be precise and concise)
        2. Which source URLs support it (match to provided sources)
        3. The original text where it appears
        4. Your confidence in this being a verifiable fact (0.0-1.0)

        Focus on concrete, verifiable facts, not opinions or subjective claims.

        Return as JSON:
        {
          "facts": [
            {
              "statement": "The hotel opened in March 2017",
              "sources": ["url1", "url2"],
              "original_text": "...opened in March 2017...",
              "confidence": 0.95
            }
          ]
        }"""

    def _get_user_prompt(self) -> str:
        return """Text to analyze:
{text}

Available source URLs:
{sources}

Extract all factual claims."""

    def _format_sources(self, links: List[dict]) -> str:
        return "\n".join([f"- {link['url']}" for link in links])