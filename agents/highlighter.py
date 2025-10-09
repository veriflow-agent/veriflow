# agents/highlighter.py
"""
Fixed Highlighter with Increased Context Window

KEY FIX: Increased from 8000 to 50000 characters per source
This allows the LLM to see much more context when finding relevant excerpts
"""
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
    """Extract relevant excerpts with LangSmith tracing and increased context"""

    def __init__(self, config):
        self.config = config

        # ✅ PROPER JSON MODE - OpenAI guarantees valid JSON
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        # ✅ SIMPLE PARSER - No fixing needed
        self.parser = JsonOutputParser(pydantic_object=HighlighterOutput)

        # Load prompts during initialization
        self.prompts = get_highlighter_prompts()

        # ✅ NEW: Increased context window
        self.max_content_chars = 50000  # Up from 8000 - GPT-4o can handle this

        fact_logger.log_component_start(
            "Highlighter", 
            model="gpt-4o",
            max_context_chars=self.max_content_chars
        )

    @traceable(
        name="highlight_excerpts",
        run_type="chain",
        tags=["excerpt-extraction", "highlighter", "semantic"]
    )
    async def highlight(self, fact: Fact, scraped_content: dict) -> dict:
        """
        Find excerpts that mention or support the fact using semantic understanding
        Returns: {url: [excerpts]}
        """
        start_time = time.time()
        results = {}

        fact_logger.logger.info(
            f"🔦 Highlighting excerpts for {fact.id}",
            extra={
                "fact_id": fact.id,
                "statement": fact.statement[:100],
                "num_sources": len(scraped_content)
            }
        )

        # Global approach: check fact against ALL scraped sources
        for url in scraped_content.keys():
            if url not in scraped_content or not scraped_content[url]:
                fact_logger.logger.warning(
                    f"⚠️ Source not found or empty: {url}",
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
                        "num_excerpts": len(excerpts),
                        "content_length_used": min(len(content), self.max_content_chars)
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
        """
        Extract excerpts from a single source using semantic understanding

        ✅ FIXED: Now uses 50K chars instead of 8K
        """

        # ✅ INCREASED CONTEXT: Use more content for better matching
        content_to_analyze = content[:self.max_content_chars]

        # Log if content was truncated
        if len(content) > self.max_content_chars:
            fact_logger.logger.warning(
                f"⚠️ Content truncated: {len(content)} → {self.max_content_chars} chars",
                extra={
                    "fact_id": fact.id,
                    "url": url,
                    "original_length": len(content),
                    "truncated_length": self.max_content_chars
                }
            )

        # ✅ CLEAN PROMPT USAGE
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts["system"]),
            ("user", self.prompts["user"])
        ])

        # ✅ FORMAT INSTRUCTIONS
        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks(f"highlighter_{fact.id}")

        # ✅ CLEAN CHAIN - No manual JSON parsing needed
        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug(
            f"🔍 Analyzing {len(content_to_analyze)} chars for excerpts",
            extra={
                "fact_id": fact.id,
                "url": url,
                "content_length": len(content_to_analyze)
            }
        )

        response = await chain.ainvoke(
            {
                "fact": fact.statement,
                "url": url,
                "content": content_to_analyze  # ✅ USING 50K CHARS NOW
            },
            config={"callbacks": callbacks.handlers}
        )

        # ✅ DIRECT DICT ACCESS - Parser returns clean dict
        excerpts = response.get('excerpts', [])

        fact_logger.logger.debug(
            f"📊 Extracted {len(excerpts)} excerpts",
            extra={
                "fact_id": fact.id,
                "url": url,
                "num_excerpts": len(excerpts)
            }
        )

        return excerpts