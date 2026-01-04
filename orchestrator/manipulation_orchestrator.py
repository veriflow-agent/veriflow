# orchestrator/manipulation_orchestrator.py
"""
Opinion Manipulation Detection Orchestrator
Coordinates the full pipeline for detecting fact manipulation in articles

Pipeline:
1. Article Analysis - Detect agenda, political lean, summary
2. Fact Extraction - Extract facts with framing context
3. Web Search Verification - Verify facts via existing pipeline
4. Manipulation Analysis - Compare verified facts to presentation
5. Report Synthesis - Create comprehensive manipulation report
6. Save audit file to R2

Reuses existing components:
- QueryGenerator for search query creation
- BraveSearcher for web search
- CredibilityFilter for source filtering
- BrowserlessScraper for content scraping
- Highlighter for excerpt extraction
- FactChecker for verification
"""

from langsmith import traceable
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config
from utils.file_manager import FileManager
from utils.job_manager import job_manager
from utils.browserless_scraper import BrowserlessScraper
from utils.brave_searcher import BraveSearcher

# Import the manipulation detector agent
from agents.manipulation_detector import (
    ManipulationDetector,
    ArticleSummary,
    ExtractedFact,
    ManipulationFinding,
    ManipulationReport
)

# Import existing agents for fact verification
from agents.query_generator import QueryGenerator
from agents.credibility_filter import CredibilityFilter
from agents.highlighter import Highlighter
from agents.fact_checker import FactChecker

# Import search audit utilities
from utils.search_audit_builder import (
    build_session_search_audit,
    build_fact_search_audit,
    build_query_audit,
    save_search_audit,
    upload_search_audit_to_r2
)


class CancelledException(Exception):
    """Raised when job is cancelled"""
    pass


class ManipulationOrchestrator:
    """
    Orchestrator for opinion manipulation detection pipeline
    
    Coordinates:
    1. ManipulationDetector agent (4 stages)
    2. Existing fact-checking components (verification)
    3. Job management and progress streaming
    4. Audit file generation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize the manipulation detector agent
        self.detector = ManipulationDetector(config)
        
        # Initialize existing fact-checking components
        self.query_generator = QueryGenerator(config)
        self.brave_searcher = BraveSearcher()
        self.credibility_filter = CredibilityFilter(config)
        self.scraper = BrowserlessScraper()
        self.highlighter = Highlighter(config)
        self.fact_checker = FactChecker(config)
        
        # File manager for audit files
        self.file_manager = FileManager()
        
        # Configuration
        self.max_sources_per_fact = config.get('max_sources_per_fact', 5)
        self.max_facts = config.get('max_facts', 5)
        
        fact_logger.log_component_start(
            "ManipulationOrchestrator",
            max_sources_per_fact=self.max_sources_per_fact,
            max_facts=self.max_facts
        )
    
    def _check_cancellation(self, job_id: str):
        """Check if job has been cancelled and raise exception if so"""
        if job_manager.is_cancelled(job_id):
            fact_logger.logger.info(f"🛑 Job {job_id} was cancelled")
            raise CancelledException(f"Job {job_id} was cancelled by user")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import random
        random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
        return f"manip_{timestamp}_{random_suffix}"
    
    @traceable(
        name="manipulation_detection_pipeline",
        run_type="chain",
        tags=["manipulation-detection", "full-pipeline"]
    )
    async def process_with_progress(
        self,
        content: str,
        job_id: str,
        source_info: str = "Unknown source"
    ) -> Dict[str, Any]:
        """
        Run the full manipulation detection pipeline with progress updates
        
        Args:
            content: Article text to analyze
            job_id: Job ID for progress tracking
            source_info: URL or source name
            
        Returns:
            Dict with manipulation report and metadata
        """
        start_time = time.time()
        session_id = self._generate_session_id()
        
        fact_logger.logger.info(
            "🚀 Starting manipulation detection pipeline",
            extra={
                "job_id": job_id,
                "session_id": session_id,
                "content_length": len(content)
            }
        )
        
        try:
            # ================================================================
            # STAGE 1: Article Analysis
            # ================================================================
            job_manager.add_progress(job_id, "📰 Analyzing article for agenda and bias...")
            self._check_cancellation(job_id)
            
            article_summary = await self.detector.analyze_article(content, source_info)
            
            job_manager.add_progress(
                job_id, 
                f"✅ Detected agenda: {article_summary.detected_agenda[:50]}..."
            )
            job_manager.add_progress(
                job_id,
                f"📊 Political lean: {article_summary.political_lean} | Opinion ratio: {article_summary.opinion_fact_ratio:.0%}"
            )
            
            # ================================================================
            # STAGE 2: Fact Extraction
            # ================================================================
            job_manager.add_progress(job_id, "🔍 Extracting key facts with framing analysis...")
            self._check_cancellation(job_id)
            
            facts = await self.detector.extract_facts(content, article_summary)
            
            if not facts:
                job_manager.add_progress(job_id, "⚠️ No verifiable facts found")
                return self._build_no_facts_result(session_id, article_summary, start_time)
            
            # Limit facts if needed
            if len(facts) > self.max_facts:
                facts = facts[:self.max_facts]
            
            job_manager.add_progress(job_id, f"✅ Extracted {len(facts)} key facts for verification")
            
            # Initialize session audit
            session_audit = build_session_search_audit(
                session_id=session_id,
                pipeline_type="manipulation_detection",
                content_country="international",
                content_language="english"
            )
            
            # ================================================================
            # STAGE 3: Fact Verification (using existing pipeline)
            # ================================================================
            job_manager.add_progress(job_id, "🌐 Starting fact verification via web search...")
            self._check_cancellation(job_id)
            
            verification_results = {}
            source_excerpts_by_fact = {}
            query_audits_by_fact = {}
            
            for i, fact in enumerate(facts, 1):
                job_manager.add_progress(
                    job_id, 
                    f"🔎 Verifying fact {i}/{len(facts)}: {fact.statement[:40]}..."
                )
                self._check_cancellation(job_id)
                
                # Run verification pipeline for this fact
                verification, excerpts, query_audits = await self._verify_fact(
                    fact=fact,
                    job_id=job_id,
                    article_summary=article_summary
                )
                
                verification_results[fact.id] = verification
                source_excerpts_by_fact[fact.id] = excerpts
                query_audits_by_fact[fact.id] = query_audits
                
                # Add to session audit
                fact_audit = build_fact_search_audit(
                    fact_id=fact.id,
                    fact_statement=fact.statement,
                    query_audits=query_audits
                )
                session_audit.add_fact_audit(fact_audit)
            
            job_manager.add_progress(job_id, "✅ Fact verification complete")
            
            # ================================================================
            # STAGE 4: Manipulation Analysis
            # ================================================================
            job_manager.add_progress(job_id, "🔬 Analyzing manipulation patterns...")
            self._check_cancellation(job_id)
            
            manipulation_findings = []
            
            for fact in facts:
                self._check_cancellation(job_id)
                
                verification = verification_results.get(fact.id, {})
                excerpts = source_excerpts_by_fact.get(fact.id, "No excerpts available")
                
                finding = await self.detector.analyze_manipulation(
                    fact=fact,
                    article_summary=article_summary,
                    verification_result=verification,
                    source_excerpts=excerpts
                )
                manipulation_findings.append(finding)
                
                if finding.manipulation_detected:
                    job_manager.add_progress(
                        job_id,
                        f"⚠️ Manipulation detected in fact {fact.id}: {finding.manipulation_severity} severity"
                    )
            
            job_manager.add_progress(job_id, "✅ Manipulation analysis complete")
            
            # ================================================================
            # STAGE 5: Report Synthesis
            # ================================================================
            job_manager.add_progress(job_id, "📊 Synthesizing final report...")
            self._check_cancellation(job_id)
            
            processing_time = time.time() - start_time
            
            report = await self.detector.synthesize_report(
                article_summary=article_summary,
                facts=facts,
                manipulation_findings=manipulation_findings,
                processing_time=processing_time
            )
            
            job_manager.add_progress(
                job_id,
                f"✅ Manipulation score: {report.overall_manipulation_score:.1f}/10"
            )
            
            # ================================================================
            # STAGE 6: Save Audit File
            # ================================================================
            job_manager.add_progress(job_id, "💾 Saving audit report...")
            
            # Save search audit
            audit_path = save_search_audit(session_audit, session_id)
            r2_url = None
            
            if audit_path:
                r2_url = upload_search_audit_to_r2(audit_path, session_id)
                if r2_url:
                    job_manager.add_progress(job_id, f"☁️ Audit saved to cloud")
            
            # Build final result
            result = self._build_result(
                session_id=session_id,
                report=report,
                facts=facts,
                verification_results=verification_results,
                r2_url=r2_url,
                start_time=start_time
            )
            
            job_manager.add_progress(job_id, "✅ Analysis complete!")
            
            fact_logger.logger.info(
                "✅ Manipulation detection pipeline complete",
                extra={
                    "session_id": session_id,
                    "manipulation_score": report.overall_manipulation_score,
                    "processing_time": round(time.time() - start_time, 2)
                }
            )
            
            return result
            
        except CancelledException:
            job_manager.add_progress(job_id, "🛑 Analysis cancelled by user")
            raise
            
        except Exception as e:
            fact_logger.logger.error(f"❌ Pipeline failed: {e}")
            import traceback
            fact_logger.logger.error(f"Traceback: {traceback.format_exc()}")
            job_manager.add_progress(job_id, f"❌ Error: {str(e)}")
            raise
    
    async def _verify_fact(
        self,
        fact: ExtractedFact,
        job_id: str,
        article_summary: ArticleSummary
    ) -> tuple[Dict[str, Any], str, List]:
        """
        Verify a single fact using the existing fact-checking pipeline
        
        Returns:
            Tuple of (verification_result, formatted_excerpts, query_audits)
        """
        query_audits = []
        
        try:
            # Step 1: Generate search queries
            # Create a fact-like object for the query generator
            fact_obj = type('Fact', (), {
                'id': fact.id,
                'statement': fact.statement
            })()
            
            queries = await self.query_generator.generate_queries(
                fact=fact_obj,
                context=f"Article agenda: {article_summary.detected_agenda}"
            )
            
            if not queries or not queries.primary_query:
                return self._empty_verification("No queries generated"), "", []
            
            # Step 2: Execute web search
            all_search_results = []
            
            # Search with primary query
            primary_results = await self.brave_searcher.search(
                queries.primary_query,
                freshness=queries.recommended_freshness
            )
            
            if primary_results and primary_results.results:
                all_search_results.extend(primary_results.results)
                query_audits.append(build_query_audit(
                    query=queries.primary_query,
                    raw_results=[r.url for r in primary_results.results],
                    freshness=queries.recommended_freshness
                ))
            
            # Search with alternative queries
            for alt_query in (queries.alternative_queries or [])[:2]:
                alt_results = await self.brave_searcher.search(alt_query)
                if alt_results and alt_results.results:
                    all_search_results.extend(alt_results.results)
                    query_audits.append(build_query_audit(
                        query=alt_query,
                        raw_results=[r.url for r in alt_results.results]
                    ))
            
            if not all_search_results:
                return self._empty_verification("No search results"), "", query_audits
            
            # Step 3: Filter by credibility
            credibility_results = await self.credibility_filter.evaluate_sources(
                fact=fact_obj,
                search_results=all_search_results
            )
            
            credible_sources = credibility_results.get_top_sources(self.max_sources_per_fact)
            credible_urls = [s.url for s in credible_sources]
            
            if not credible_urls:
                return self._empty_verification("No credible sources found"), "", query_audits
            
            # Step 4: Scrape sources
            scraped_content = await self.scraper.scrape_urls_for_facts(credible_urls)
            
            if not scraped_content or not any(scraped_content.values()):
                return self._empty_verification("Failed to scrape sources"), "", query_audits
            
            # Step 5: Extract relevant excerpts
            all_excerpts = []
            source_metadata = credibility_results.get_source_metadata_dict()
            
            for url, content in scraped_content.items():
                if not content:
                    continue
                    
                excerpts = await self.highlighter.extract_excerpts(
                    fact=fact.statement,
                    url=url,
                    content=content
                )
                
                if excerpts:
                    tier = source_metadata.get(url, {}).get('tier', 'unknown')
                    for excerpt in excerpts:
                        all_excerpts.append({
                            'url': url,
                            'tier': tier,
                            'quote': excerpt.get('quote', ''),
                            'relevance': excerpt.get('relevance', 0.5)
                        })
            
            if not all_excerpts:
                return self._empty_verification("No relevant excerpts found"), "", query_audits
            
            # Step 6: Verify fact
            # Sort excerpts by tier and relevance
            all_excerpts.sort(key=lambda x: (
                0 if x['tier'] == 'tier1' else 1 if x['tier'] == 'tier2' else 2,
                -x['relevance']
            ))
            
            # Format excerpts for fact checker
            formatted_excerpts = self._format_excerpts_for_checker(all_excerpts)
            
            verification = await self.fact_checker.verify(
                fact=fact.statement,
                excerpts=formatted_excerpts
            )
            
            # Build result
            result = {
                'match_score': verification.match_score if verification else 0.5,
                'confidence': verification.confidence if verification else 0.5,
                'report': verification.report if verification else "Verification incomplete",
                'sources_used': credible_urls,
                'excerpts': formatted_excerpts
            }
            
            return result, formatted_excerpts, query_audits
            
        except Exception as e:
            fact_logger.logger.error(f"❌ Fact verification failed: {e}")
            return self._empty_verification(f"Error: {str(e)}"), "", query_audits
    
    def _empty_verification(self, reason: str) -> Dict[str, Any]:
        """Return empty verification result"""
        return {
            'match_score': 0.5,
            'confidence': 0.0,
            'report': reason,
            'sources_used': [],
            'excerpts': ""
        }
    
    def _format_excerpts_for_checker(self, excerpts: List[Dict]) -> str:
        """Format excerpts for the fact checker"""
        lines = []
        
        for excerpt in excerpts[:10]:  # Limit to 10 excerpts
            tier_label = excerpt['tier'].upper() if excerpt['tier'] else 'UNKNOWN'
            lines.append(f"[{tier_label}] {excerpt['url']}")
            lines.append(f"  \"{excerpt['quote'][:500]}...\"" if len(excerpt['quote']) > 500 else f"  \"{excerpt['quote']}\"")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_no_facts_result(
        self,
        session_id: str,
        article_summary: ArticleSummary,
        start_time: float
    ) -> Dict[str, Any]:
        """Build result when no facts were extracted"""
        return {
            'success': True,
            'session_id': session_id,
            'article_summary': {
                'main_thesis': article_summary.main_thesis,
                'political_lean': article_summary.political_lean,
                'detected_agenda': article_summary.detected_agenda,
                'opinion_fact_ratio': article_summary.opinion_fact_ratio,
                'emotional_tone': article_summary.emotional_tone
            },
            'manipulation_score': 0.0,
            'facts_analyzed': [],
            'manipulation_findings': [],
            'report': {
                'overall_score': 0.0,
                'justification': "No verifiable facts could be extracted from the article",
                'techniques_used': [],
                'what_got_right': ["Article may be purely opinion-based"],
                'misleading_elements': [],
                'recommendation': "This article appears to contain no verifiable factual claims."
            },
            'processing_time': time.time() - start_time,
            'r2_url': None
        }
    
    def _build_result(
        self,
        session_id: str,
        report: ManipulationReport,
        facts: List[ExtractedFact],
        verification_results: Dict[str, Dict],
        r2_url: Optional[str],
        start_time: float
    ) -> Dict[str, Any]:
        """Build the final result dictionary"""
        
        # Format facts for response
        facts_data = []
        for fact in facts:
            verification = verification_results.get(fact.id, {})
            facts_data.append({
                'id': fact.id,
                'statement': fact.statement,
                'original_text': fact.original_text,
                'framing': fact.framing,
                'context_given': fact.context_given,
                'context_potentially_omitted': fact.context_potentially_omitted,
                'manipulation_potential': fact.manipulation_potential,
                'verification': {
                    'match_score': verification.get('match_score', 0.5),
                    'sources_used': verification.get('sources_used', [])
                }
            })
        
        # Format manipulation findings
        findings_data = []
        for finding in report.facts_analyzed:
            findings_data.append({
                'fact_id': finding.fact_id,
                'fact_statement': finding.fact_statement,
                'truthfulness': finding.truthfulness,
                'truth_score': finding.truth_score,
                'manipulation_detected': finding.manipulation_detected,
                'manipulation_types': finding.manipulation_types,
                'manipulation_severity': finding.manipulation_severity,
                'what_was_omitted': finding.what_was_omitted,
                'how_it_serves_agenda': finding.how_it_serves_agenda,
                'corrected_context': finding.corrected_context,
                'sources_used': finding.sources_used
            })
        
        return {
            'success': True,
            'session_id': session_id,
            'article_summary': {
                'main_thesis': report.article_summary.main_thesis,
                'political_lean': report.article_summary.political_lean,
                'detected_agenda': report.article_summary.detected_agenda,
                'opinion_fact_ratio': report.article_summary.opinion_fact_ratio,
                'emotional_tone': report.article_summary.emotional_tone,
                'target_audience': report.article_summary.target_audience,
                'rhetorical_strategies': report.article_summary.rhetorical_strategies,
                'summary': report.article_summary.summary
            },
            'manipulation_score': report.overall_manipulation_score,
            'facts_analyzed': facts_data,
            'manipulation_findings': findings_data,
            'report': {
                'overall_score': report.overall_manipulation_score,
                'justification': report.score_justification,
                'techniques_used': report.manipulation_techniques_used,
                'what_got_right': report.what_article_got_right,
                'misleading_elements': report.key_misleading_elements,
                'agenda_alignment': report.agenda_alignment_analysis,
                'recommendation': report.reader_recommendation,
                'confidence': report.confidence
            },
            'processing_time': report.processing_time,
            'r2_url': r2_url
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_manipulation_orchestrator(config: Optional[Dict] = None) -> ManipulationOrchestrator:
    """
    Factory function to create a ManipulationOrchestrator instance
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured ManipulationOrchestrator instance
    """
    default_config = {
        'max_sources_per_fact': 5,
        'max_facts': 5
    }
    
    if config:
        default_config.update(config)
    
    return ManipulationOrchestrator(default_config)
