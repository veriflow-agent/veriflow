# orchestrator/web_search_orchestrator.py
"""
Web Search Orchestrator - WITH COMPREHENSIVE SEARCH AUDIT
Coordinates web search-based fact verification pipeline for text without links

UPDATES:
- ✅ Tracks all raw Brave Search results
- ✅ Records filtered sources with reasoning
- ✅ Records credible sources with tier assignments
- ✅ Saves comprehensive audit file

Pipeline:
1. Extract facts from plain text (with country/language detection)
2. Generate search queries for each fact (with multi-language support)
3. Execute web searches via Brave → AUDIT: Track all raw results
4. Filter results by source credibility → AUDIT: Track filtered + credible
5. Scrape credible sources → AUDIT: Track scrape success/failure
6. Combine content into verification corpus
7. Check facts against combined content
8. Save comprehensive search audit → NEW
"""

from langsmith import traceable
import time
import asyncio
from typing import List, Dict, Any, Optional

from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config
from utils.file_manager import FileManager
from utils.job_manager import job_manager
from utils.browserless_scraper import FactCheckScraper
from utils.brave_searcher import BraveSearcher

# Import agents
from agents.fact_extractor import FactAnalyzer, ContentLocation
from agents.fact_checker import FactChecker
from agents.query_generator import QueryGenerator
from agents.credibility_filter import CredibilityFilter

# NEW: Import search audit utilities
from utils.search_audit_builder import (
    build_session_search_audit,
    build_fact_search_audit,
    build_query_audit,
    save_search_audit,
    upload_search_audit_to_r2
)


class WebSearchOrchestrator:
    """
    Orchestrator for web search-based fact verification

    For plain text input without provided sources
    Supports multi-language queries for non-English content

    NEW: Comprehensive search audit tracking
    """

    def __init__(self, config):
        self.config = config

        # Initialize all agents
        self.analyzer = FactAnalyzer(config)
        self.query_generator = QueryGenerator(config)
        self.searcher = BraveSearcher(config, max_results=5)
        self.credibility_filter = CredibilityFilter(config, min_credibility_score=0.70)
        self.scraper = FactCheckScraper(config)
        self.checker = FactChecker(config)
        self.file_manager = FileManager()

        # Configuration
        self.max_sources_per_fact = 10  # Maximum sources to scrape per fact
        self.max_concurrent_scrapes = 5  # Limit concurrent scraping

        # NEW: Initialize R2 uploader for audit upload
        try:
            from utils.r2_uploader import R2Uploader
            self.r2_uploader = R2Uploader()
            self.r2_enabled = True
            fact_logger.logger.info("✅ R2 uploader initialized for search audits")
        except Exception as e:
            self.r2_enabled = False
            fact_logger.logger.warning(f"⚠️ R2 not available for audits: {e}")

        fact_logger.log_component_start(
            "WebSearchOrchestrator",
            max_sources_per_fact=self.max_sources_per_fact
        )

    def _check_cancellation(self, job_id: str):
        """Check if job has been cancelled and raise exception if so"""
        job = job_manager.get_job(job_id)
        if job and job.get('status') == 'cancelled':
            raise Exception("Job cancelled by user")

    def _create_empty_result(self, session_id: str, message: str) -> dict:
        """Create an empty result for cases with no facts"""
        return {
            "success": True,
            "session_id": session_id,
            "facts": [],
            "summary": {"message": message},
            "processing_time": 0,
            "methodology": "web_search_verification",
            "statistics": {}
        }

    def _generate_summary(self, results: list) -> dict:
        """Generate summary statistics from results"""
        if not results:
            return {"message": "No results to summarize"}

        scores = [r.match_score for r in results]
        return {
            "total_facts": len(results),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "verified_count": len([r for r in results if r.match_score >= 0.9]),
            "partial_count": len([r for r in results if 0.7 <= r.match_score < 0.9]),
            "unverified_count": len([r for r in results if r.match_score < 0.7])
        }

    async def process_with_progress(self, text_content: str, job_id: str) -> dict:
        """Process with real-time progress updates, multi-language support, and search audit"""
        from utils.job_manager import job_manager

        session_id = self.file_manager.create_session()
        start_time = time.time()

        # NEW: Initialize session search audit
        session_audit = None

        try:
            # Step 1: Extract Facts (now includes country/language detection)
            job_manager.add_progress(job_id, "📄 Extracting facts from text...")
            self._check_cancellation(job_id)

            parsed_input = {
                'text': text_content,
                'links': [],
                'format': 'plain_text'
            }

            facts, _, content_location = await self.analyzer.analyze(parsed_input)

            if not facts:
                job_manager.add_progress(job_id, "⚠️ No verifiable facts found")
                return self._create_empty_result(session_id, "No verifiable facts found in text")

            job_manager.add_progress(job_id, f"✅ Extracted {len(facts)} facts")

            # NEW: Initialize session audit with content location
            session_audit = build_session_search_audit(
                session_id=session_id,
                pipeline_type="web_search",
                content_country=content_location.country if content_location else "international",
                content_language=content_location.language if content_location else "english"
            )

            # Log detected location
            if content_location.country != "international":
                if content_location.language != "english":
                    job_manager.add_progress(
                        job_id, 
                        f"🌍 Detected location: {content_location.country} ({content_location.language}) - will include local language queries"
                    )
                else:
                    job_manager.add_progress(
                        job_id, 
                        f"🌍 Detected location: {content_location.country} (English)"
                    )

            # Step 2: Generate Search Queries (now with multi-language support)
            job_manager.add_progress(job_id, "🔍 Generating search queries...")
            self._check_cancellation(job_id)

            all_queries_by_fact = {}
            for fact in facts:
                queries = await self.query_generator.generate_queries(
                    fact,
                    content_location=content_location
                )
                all_queries_by_fact[fact.id] = queries

            total_queries = sum(
                len(q.all_queries) for q in all_queries_by_fact.values()
            )
            job_manager.add_progress(job_id, f"✅ Generated {total_queries} queries")

            # Step 3: Execute Searches (with multi-language queries)
            job_manager.add_progress(job_id, "🌐 Searching the web...")
            self._check_cancellation(job_id)

            search_results_by_fact = {}
            query_audits_by_fact = {}  # NEW: Track query audits per fact
            total_results = 0

            for fact in facts:
                queries = all_queries_by_fact[fact.id]
                search_results = await self.searcher.search_multiple(
                    queries=queries.all_queries,
                    search_depth="advanced",
                    max_concurrent=3
                )
                search_results_by_fact[fact.id] = search_results

                # NEW: Build query audits for this fact
                fact_query_audits = []
                for query, brave_results in search_results.items():
                    # Determine query type
                    query_type = "english"
                    if queries.local_queries and query in queries.local_queries:
                        query_type = "local_language"
                    elif queries.fallback_query and query == queries.fallback_query:
                        query_type = "fallback"

                    qa = build_query_audit(
                        query=query,
                        brave_results=brave_results,
                        query_type=query_type,
                        language=content_location.language if content_location else "en"
                    )
                    fact_query_audits.append(qa)
                    total_results += len(brave_results.results)

                query_audits_by_fact[fact.id] = fact_query_audits

            job_manager.add_progress(job_id, f"📊 Found {total_results} potential sources")

            # Step 4: Filter by Credibility
            job_manager.add_progress(job_id, "🏆 Filtering sources by credibility...")
            self._check_cancellation(job_id)

            credible_urls_by_fact = {}
            credibility_results_by_fact = {}  # NEW: Store full credibility results

            for fact in facts:
                all_results_for_fact = []
                for query, results in search_results_by_fact[fact.id].items():
                    all_results_for_fact.extend(results.results)

                if not all_results_for_fact:
                    credible_urls_by_fact[fact.id] = []
                    credibility_results_by_fact[fact.id] = None
                    continue

                credibility_results = await self.credibility_filter.evaluate_sources(
                    fact=fact,
                    search_results=all_results_for_fact
                )
                credibility_results_by_fact[fact.id] = credibility_results

                credible_urls = credibility_results.get_top_sources(self.max_sources_per_fact)
                credible_urls_by_fact[fact.id] = [s.url for s in credible_urls]

            total_credible = sum(len(urls) for urls in credible_urls_by_fact.values())
            job_manager.add_progress(job_id, f"✅ Found {total_credible} credible sources")

            # Step 5: Scrape Sources
            job_manager.add_progress(job_id, f"🌐 Scraping {total_credible} sources...")
            self._check_cancellation(job_id)

            scraped_content_by_fact = {}
            scraped_urls_by_fact = {}  # NEW: Track successfully scraped URLs
            scrape_errors_by_fact = {}  # NEW: Track scrape errors

            for fact in facts:
                urls_to_scrape = credible_urls_by_fact.get(fact.id, [])
                if urls_to_scrape:
                    scraped_content = await self.scraper.scrape_urls_for_facts(urls_to_scrape)
                    scraped_content_by_fact[fact.id] = scraped_content

                    # NEW: Track which URLs were successfully scraped
                    scraped_urls_by_fact[fact.id] = [
                        url for url, content in scraped_content.items()
                        if content  # Non-empty content means success
                    ]
                    scrape_errors_by_fact[fact.id] = {
                        url: "Scrape failed or empty content"
                        for url in urls_to_scrape
                        if url not in scraped_urls_by_fact[fact.id]
                    }

            job_manager.add_progress(job_id, "✅ Scraping complete")

            # NEW: Build fact search audits BEFORE verification
            for fact in facts:
                fact_audit = build_fact_search_audit(
                    fact_id=fact.id,
                    fact_statement=fact.statement,
                    query_audits=query_audits_by_fact.get(fact.id, []),
                    credibility_results=credibility_results_by_fact.get(fact.id),
                    scraped_urls=scraped_urls_by_fact.get(fact.id, []),
                    scrape_errors=scrape_errors_by_fact.get(fact.id, {})
                )
                session_audit.add_fact_audit(fact_audit)

            # Step 6: Verify Facts (Parallel processing with asyncio.gather)
            job_manager.add_progress(
                job_id,
                f"⚖️ Verifying {len(facts)} facts in parallel..."
            )
            self._check_cancellation(job_id)

            async def verify_single_fact(fact, fact_index):
                """Verify a single fact and return result"""
                try:
                    scraped_content = scraped_content_by_fact.get(fact.id, {})
                    cred_results = credibility_results_by_fact.get(fact.id)
                    source_metadata = cred_results.source_metadata if cred_results else {}

                    if not scraped_content or not any(scraped_content.values()):
                        from agents.fact_checker import FactCheckResult
                        result = FactCheckResult(
                            fact_id=fact.id,
                            statement=fact.statement,
                            match_score=0.0,
                            confidence=0.0,
                            report="Unable to verify - no credible sources found. Web search did not yield sources that could be successfully scraped."
                        )
                        job_manager.add_progress(job_id, f"⚠️ {fact.id}: No sources")
                        return result

                    # Run highlighter to extract relevant excerpts
                    excerpts = await self.checker.highlighter.extract_excerpts(
                        fact=fact,
                        scraped_content=scraped_content
                    ) if hasattr(self.checker, 'highlighter') else scraped_content

                    result = await self.checker.check_fact(
                        fact=fact,
                        excerpts=excerpts if isinstance(excerpts, dict) else scraped_content,
                        source_metadata=source_metadata
                    )

                    score_emoji = "✅" if result.match_score >= 0.9 else "⚠️" if result.match_score >= 0.7 else "❌"
                    job_manager.add_progress(
                        job_id,
                        f"{score_emoji} {fact.id}: {result.match_score:.0%} verified"
                    )
                    return result

                except Exception as e:
                    fact_logger.logger.error(f"Error verifying {fact.id}: {e}")
                    from agents.fact_checker import FactCheckResult
                    return FactCheckResult(
                        fact_id=fact.id,
                        statement=fact.statement,
                        match_score=0.0,
                        confidence=0.0,
                        report=f"Verification error: {str(e)}"
                    )

            # Create verification tasks
            tasks = [
                verify_single_fact(fact, i)
                for i, fact in enumerate(facts)
            ]

            # Execute all verifications in parallel
            results = await asyncio.gather(*tasks)

            job_manager.add_progress(job_id, "✅ All facts verified")

            # Step 7: Generate Summary
            processing_time = time.time() - start_time
            summary = self._generate_summary(results)

            # NEW: Save search audit
            job_manager.add_progress(job_id, "📋 Saving search audit...")

            audit_file_path = save_search_audit(
                session_audit=session_audit,
                file_manager=self.file_manager,
                session_id=session_id,
                filename="search_audit.json"
            )

            # NEW: Upload audit to R2 if available
            audit_r2_url = None
            if self.r2_enabled:
                audit_r2_url = await upload_search_audit_to_r2(
                    session_audit=session_audit,
                    session_id=session_id,
                    r2_uploader=self.r2_uploader,
                    pipeline_type="web-search"
                )

            job_manager.add_progress(job_id, f"✅ Complete in {processing_time:.1f}s")

            return {
                "success": True,
                "session_id": session_id,
                "facts": [
                    {
                        "id": r.fact_id,
                        "statement": r.statement,
                        "match_score": r.match_score,
                        "confidence": r.confidence,
                        "report": r.report,
                        "tier_breakdown": r.tier_breakdown
                    }
                    for r in results
                ],
                "summary": summary,
                "processing_time": processing_time,
                "methodology": "web_search_verification",
                "content_location": {
                    "country": content_location.country,
                    "language": content_location.language
                } if content_location else None,
                "statistics": {
                    "facts_extracted": len(facts),
                    "queries_generated": total_queries,
                    "raw_results_found": total_results,
                    "credible_sources": total_credible,
                    "facts_verified": len(results)
                },
                # NEW: Audit information
                "audit": {
                    "local_path": audit_file_path,
                    "r2_url": audit_r2_url,
                    "summary": {
                        "total_raw_results": session_audit.total_raw_results,
                        "total_credible": session_audit.total_credible_sources,
                        "total_filtered": session_audit.total_filtered_sources,
                        "tier_breakdown": {
                            "tier1": session_audit.total_tier1,
                            "tier2": session_audit.total_tier2,
                            "tier3_filtered": session_audit.total_tier3_filtered
                        }
                    }
                }
            }

        except Exception as e:
            error_msg = str(e)
            if "cancelled" in error_msg.lower():
                job_manager.add_progress(job_id, "🛑 Verification cancelled")
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": "Cancelled by user",
                    "processing_time": time.time() - start_time
                }

            fact_logger.logger.error(f"Web search orchestrator error: {e}")
            job_manager.add_progress(job_id, f"❌ Error: {error_msg}")

            # NEW: Try to save partial audit even on error
            if session_audit and session_audit.total_facts > 0:
                try:
                    save_search_audit(
                        session_audit=session_audit,
                        file_manager=self.file_manager,
                        session_id=session_id,
                        filename="search_audit_partial.json"
                    )
                except:
                    pass  # Don't fail on audit save error

            return {
                "success": False,
                "session_id": session_id,
                "error": error_msg,
                "processing_time": time.time() - start_time
            }