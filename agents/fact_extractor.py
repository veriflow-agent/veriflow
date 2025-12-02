# agents/fact_extractor.py
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Optional
import time

from prompts.fact_extractor_prompts import get_analyzer_prompts
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config


class Fact(BaseModel):
    id: str
    statement: str
    sources: List[str]  # Will be empty in global approach
    original_text: str
    confidence: float


class ContentLocation(BaseModel):
    """Geographic and language context for the content"""
    country: str = Field(default="international", description="Primary country where events take place")
    country_code: str = Field(default="", description="ISO 2-letter country code")
    language: str = Field(default="english", description="Primary language for that country")
    confidence: float = Field(default=0.5, description="Confidence in location detection")


class GlobalAnalyzerOutput(BaseModel):
    facts: List[dict] = Field(description="List of extracted facts")
    all_sources: List[str] = Field(description="All source URLs mentioned")
    content_location: Optional[dict] = Field(default=None, description="Country and language info")


class FactAnalysisResult(BaseModel):
    """Complete result from fact analysis including location context"""
    facts: List[Fact]
    all_sources: List[str]
    content_location: ContentLocation


class FactAnalyzer:
    """Extract factual claims with global source checking, large file support, and location detection"""

    def __init__(self, config):
        self.config = config

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        ).bind(response_format={"type": "json_object"})

        self.parser = JsonOutputParser(pydantic_object=GlobalAnalyzerOutput)

        # Load prompts from external file
        self.prompts = get_analyzer_prompts()

        # Context window limits (conservative estimates)
        self.max_input_tokens = 100000  # GPT-4o-mini context limit
        self.tokens_per_char = 0.25     # Rough estimate: 4 chars per token
        self.max_input_chars = int(self.max_input_tokens / self.tokens_per_char)

        fact_logger.log_component_start("FactAnalyzer", model="gpt-4o-mini")

    @traceable(
        name="analyze_facts",
        run_type="chain",
        tags=["fact-extraction", "analyzer", "global-approach"]
    )
    async def analyze(self, parsed_content: dict) -> tuple[List[Fact], List[str], ContentLocation]:
        """
        Extract facts, return all source URLs, and detect content location (GLOBAL APPROACH with chunking)

        Returns: (facts_list, all_source_urls, content_location)
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
            # Check if content fits in context window
            text_length = len(parsed_content['text'])

            if text_length > self.max_input_chars:
                fact_logger.logger.info(
                    f"📄 Large content detected ({text_length} chars), using chunking approach",
                    extra={"text_length": text_length, "max_chars": self.max_input_chars}
                )
                facts, all_sources, content_location = await self._analyze_with_chunking(parsed_content)
            else:
                facts, all_sources, content_location = await self._analyze_single_pass(parsed_content)

            duration = time.time() - start_time
            fact_logger.log_component_complete(
                "FactAnalyzer",
                duration,
                num_facts=len(facts),
                total_sources=len(all_sources),
                approach="global",
                detected_country=content_location.country,
                detected_language=content_location.language
            )

            fact_logger.logger.info(
                f"🌍 Content location detected: {content_location.country} ({content_location.language})",
                extra={
                    "country": content_location.country,
                    "language": content_location.language,
                    "confidence": content_location.confidence
                }
            )

            return facts, all_sources, content_location

        except Exception as e:
            fact_logger.log_component_error("FactAnalyzer", e)
            raise

    async def _analyze_single_pass(self, parsed_content: dict) -> tuple[List[Fact], List[str], ContentLocation]:
        """Analyze content that fits in a single context window"""

        # Use prompts from external file, modified for global approach
        system_prompt = self.prompts["system"].replace(
            "Map it to the source URL(s) that supposedly support it",
            "Note: Source verification will happen globally across all sources"
        ).replace(
            "Match facts to ALL relevant source URLs mentioned nearby",
            "Focus on extracting verifiable facts, not mapping to specific sources"
        )

        user_prompt = self.prompts["user"].replace(
            "Match each fact to its supporting source URL(s)",
            "Extract facts without mapping to specific sources"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + "\n\nIMPORTANT: You MUST return valid JSON only. No other text."),
            ("user", user_prompt + "\n\n{format_instructions}\n\nReturn your response as valid JSON.")
        ])

        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )

        callbacks = langsmith_config.get_callbacks("fact_analyzer")
        chain = prompt_with_format | self.llm | self.parser

        fact_logger.logger.debug("🔗 Invoking LangChain with global approach (single pass)")

        try:
            response = await chain.ainvoke(
                {
                    "text": parsed_content['text'],
                    "sources": self._format_sources(parsed_content['links'])
                },
                config={"callbacks": callbacks.handlers}
            )

            return self._process_response(response, parsed_content)

        except Exception as e:
            fact_logger.logger.error(f"❌ LLM invocation failed: {e}")
            import traceback
            fact_logger.logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def _analyze_with_chunking(self, parsed_content: dict) -> tuple[List[Fact], List[str], ContentLocation]:
        """Analyze large content by splitting into chunks"""

        text = parsed_content['text']
        chunk_size = self.max_input_chars - 10000  # Reserve space for prompts

        chunks = self._split_into_chunks(text, chunk_size)

        fact_logger.logger.info(
            f"📄 Split content into {len(chunks)} chunks",
            extra={"num_chunks": len(chunks)}
        )

        all_facts = []
        all_location_votes = []  # Collect location from each chunk

        for i, chunk in enumerate(chunks, 1):
            fact_logger.logger.debug(f"🔍 Analyzing chunk {i}/{len(chunks)}")

            chunk_parsed = {
                'text': chunk,
                'links': parsed_content['links'],
                'format': parsed_content.get('format', 'unknown')
            }

            chunk_facts, _, chunk_location = await self._analyze_single_pass(chunk_parsed)
            all_facts.extend(chunk_facts)
            all_location_votes.append(chunk_location)

        # Deduplicate facts
        unique_facts = self._deduplicate_facts(all_facts)

        # Get all sources from parsed content
        all_sources = [link['url'] for link in parsed_content['links']]

        # Aggregate location votes (use most confident or most common)
        content_location = self._aggregate_location_votes(all_location_votes)

        return unique_facts, all_sources, content_location

    def _aggregate_location_votes(self, location_votes: List[ContentLocation]) -> ContentLocation:
        """Aggregate location detections from multiple chunks"""
        if not location_votes:
            return ContentLocation()

        # Find the vote with highest confidence
        best_vote = max(location_votes, key=lambda x: x.confidence)

        # If all chunks agree, boost confidence
        countries = [v.country for v in location_votes if v.country != "international"]
        if countries and all(c == countries[0] for c in countries):
            best_vote.confidence = min(1.0, best_vote.confidence + 0.1)

        return best_vote

    def _split_into_chunks(self, text: str, chunk_size: int, overlap: int = 500) -> List[str]:
        """Split text into overlapping chunks at sentence boundaries"""

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                # Find sentence boundary near the end
                boundary_search = text[max(0, end-200):end]
                sentence_endings = ['. ', '! ', '? ', '\n\n']

                best_boundary = end
                for ending in sentence_endings:
                    pos = boundary_search.rfind(ending)
                    if pos != -1:
                        actual_pos = max(0, end-200) + pos + 1
                        if abs(actual_pos - end) < abs(best_boundary - end):
                            best_boundary = actual_pos

                end = min(best_boundary, len(text))

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Next chunk starts with overlap
            start = max(start + 1, end - overlap)

            if end >= len(text):
                break

        return chunks

    def _deduplicate_facts(self, facts: List[Fact]) -> List[Fact]:
        """Remove duplicate facts based on statement similarity"""
        unique_facts = []
        seen_statements = set()

        for fact in facts:
            statement_key = fact.statement.lower().strip()

            if statement_key not in seen_statements:
                seen_statements.add(statement_key)
                unique_facts.append(fact)

        # Re-number the facts
        for i, fact in enumerate(unique_facts):
            fact.id = f"fact{i+1}"

        return unique_facts

    def _process_response(self, response: dict, parsed_content: dict) -> tuple[List[Fact], List[str], ContentLocation]:
        """Convert response to Fact objects, extract sources, and parse location"""

        # Check for error in response
        if 'error' in response:
            error_msg = response.get('error', 'Unknown error')
            fact_logger.logger.error(f"❌ LLM returned error: {error_msg}")
            raise ValueError(f"LLM error: {error_msg}")

        # Ensure we have facts key
        if 'facts' not in response:
            fact_logger.logger.error(f"❌ Missing 'facts' in response: {response}")
            raise ValueError(f"Invalid response structure: missing 'facts' key. Got: {list(response.keys())}")

        # Convert to Fact objects
        facts = []
        for i, fact_data in enumerate(response.get('facts', [])):
            try:
                fact = Fact(
                    id=f"fact{i+1}",
                    statement=fact_data['statement'],
                    sources=[],  # Empty for global approach
                    original_text=fact_data.get('original_text', ''),
                    confidence=fact_data.get('confidence', 1.0)
                )
                facts.append(fact)

                fact_logger.logger.debug(
                    f"📝 Extracted fact {fact.id}",
                    extra={
                        "fact_id": fact.id,
                        "statement": fact.statement[:100]
                    }
                )
            except KeyError as e:
                fact_logger.logger.error(f"❌ Missing required field in fact_data: {e}")
                continue

        # Get all source URLs
        all_sources = response.get('all_sources', [])
        if not all_sources:
            all_sources = [link['url'] for link in parsed_content['links']]

        # Parse content location
        content_location = self._parse_content_location(response)

        return facts, all_sources, content_location

    def _parse_content_location(self, response: dict) -> ContentLocation:
        """Parse content location from response"""
        location_data = response.get('content_location', {})

        if not location_data:
            fact_logger.logger.debug("No content_location in response, using defaults")
            return ContentLocation()

        try:
            return ContentLocation(
                country=location_data.get('country', 'international'),
                country_code=location_data.get('country_code', ''),
                language=location_data.get('language', 'english').lower(),
                confidence=location_data.get('confidence', 0.5)
            )
        except Exception as e:
            fact_logger.logger.warning(f"Failed to parse content_location: {e}")
            return ContentLocation()

    def _format_sources(self, links: List[dict]) -> str:
        """Format source links for the prompt"""
        return "\n".join([f"- {link['url']}" for link in links])