# agents/highlighter.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import time

from utils.langsmith_config import langsmith_config
from utils.logger import fact_logger
from agents.analyser import Fact
from prompts.highlighter_prompts import get_highlighter_prompts

class HighlighterOutput(BaseModel):
    excerpts: List[Dict[str, Any]] = Field(description="List of relevant excerpts")

class Highlighter:
    """Extract relevant excerpts with LangSmith tracing"""

    def __init__(self, config):
        self.config = config

        # ✅ PROPER JSON MODE - OpenAI guarantees valid JSON
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        # ✅ SIMPLE PARSER - No fixing needed
        self.parser = JsonOutputParser(pydantic_object=HighlighterOutput)

        # Load prompts during initialization
        self.prompts = get_highlighter_prompts()

        fact_logger.log_component_start("Highlighter", model="gpt-4o-mini")

    @traceable(
        name="highlight_excerpts",
        run_type="chain",
        tags=["excerpt-extraction", "highlighter"]
    )
    async def highlight(self, fact: Fact, scraped_content: dict) -> dict:
        """
        Find excerpts that mention or support the fact
        Returns: {url: [excerpts]}
        """
        start_time = time.time()
        results = {}

        fact_logger.logger.info(
            f"🔦 Highlighting excerpts for {fact.id}",
            extra={
                "fact_id": fact.id,
                "statement": fact.statement[:100],
                "num_sources": len(fact.sources)
            }
        )

        for url in fact.sources:
            if url not in scraped_content:
                fact_logger.logger.warning(
                    f"⚠️ Source not found in scraped content: {url}",
                    extra={"fact_id": fact.id, "url": url}
                )
                continue

            content = scraped_content[url]

            try:
                excerpts = await self._extract_excerpts(fact, url, content)
                results[url] = excerpts

                fact_logger.logger.debug(
                    f"✂️ Found {len(excerpts)} excerpts from {url}",
                    extra={
                        "fact_id": fact.id,
                        "url": url,
                        "num_excerpts": len(excerpts)
                    }
                )

            except Exception as e:
                fact_logger.logger.error(
                    f"❌ Failed to extract excerpts from {url}: {e}",
                    extra={"fact_id": fact.id, "url": url, "error": str(e)}
                )
                results[url] = []

        duration = time.time() - start_time
        total_excerpts = sum(len(excerpts) for excerpts in results.values())

        fact_logger.log_component_complete(
            "Highlighter",
            duration,
            fact_id=fact.id,
            total_excerpts=total_excerpts,
            sources_processed=len(results)
        )

        return results

    @traceable(name="extract_single_excerpt", run_type="llm")
    async def _extract_excerpts(self, fact: Fact, url: str, content: str) -> list:
        """Extract excerpts from a single source"""

        # ✅ CLEAN PROMPT USAGE - No injection here
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts["system"]),
            ("user", self.prompts["user"])
        ])

        # ✅ FORMAT INSTRUCTIONS
        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        # ✅ FORMAT INSTRUCTIONS
        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"highlighter_{fact.id}")

        # ✅ CLEAN CHAIN - No manual JSON parsing needed
        chain = prompt_with_format | self.llm | self.parser

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "url": url,
                "content": content[:8000]
            },
            config={"callbacks": callbacks.handlers}
        )

        # ✅ DIRECT DICT ACCESS - Parser returns clean dict
        return response.get('excerpts', [])