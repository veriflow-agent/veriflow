# utils/search_audit_builder.py
"""
Search Audit Builder
Helper functions to build and save search audits from orchestrator data

Used by: WebSearchOrchestrator, KeyClaimsOrchestrator
"""

from typing import List, Dict, Any, Optional
from utils.search_audit import (
    SessionSearchAudit,
    FactSearchAudit,
    QueryAudit,
    RawSearchResult,
    CredibleSource,
    FilteredSource,
    create_raw_search_result,
    create_credible_source,
    create_filtered_source
)
from utils.logger import fact_logger


def build_query_audit(
    query: str,
    brave_results,  # BraveSearchResults object
    query_type: str = "english",
    language: str = "en"
) -> QueryAudit:
    """
    Build a QueryAudit from Brave Search results
    
    Args:
        query: The search query string
        brave_results: BraveSearchResults object from BraveSearcher
        query_type: Type of query (english, local_language, fallback)
        language: Language code
    
    Returns:
        QueryAudit with all raw results
    """
    raw_results = []
    
    for i, result in enumerate(brave_results.results, 1):
        raw = create_raw_search_result(result, position=i, query=query)
        raw_results.append(raw)
    
    return QueryAudit(
        query=query,
        query_type=query_type,
        language=language,
        results_count=len(raw_results),
        search_time_seconds=brave_results.search_time,
        raw_results=raw_results
    )


def build_fact_search_audit(
    fact_id: str,
    fact_statement: str,
    query_audits: List[QueryAudit],
    credibility_results,  # CredibilityResults from CredibilityFilter
    scraped_urls: List[str] = None,
    scrape_errors: Dict[str, str] = None
) -> FactSearchAudit:
    """
    Build a FactSearchAudit from orchestrator data
    
    Args:
        fact_id: Unique identifier for the fact
        fact_statement: The fact statement text
        query_audits: List of QueryAudit objects for all queries
        credibility_results: CredibilityResults from CredibilityFilter.evaluate_sources()
        scraped_urls: List of URLs that were successfully scraped
        scrape_errors: Dict of URL -> error message for failed scrapes
    
    Returns:
        FactSearchAudit with all data populated
    """
    scraped_urls = scraped_urls or []
    scrape_errors = scrape_errors or {}
    
    fact_audit = FactSearchAudit(
        fact_id=fact_id,
        fact_statement=fact_statement,
        queries=query_audits
    )
    
    # Collect all unique URLs across queries
    unique_urls = set()
    for qa in query_audits:
        for raw in qa.raw_results:
            unique_urls.add(raw.url)
    fact_audit.total_unique_urls = len(unique_urls)
    
    # Build URL to query mapping (which query found each URL)
    url_to_query = {}
    for qa in query_audits:
        for raw in qa.raw_results:
            if raw.url not in url_to_query:
                url_to_query[raw.url] = qa.query
    
    # Process credibility evaluations
    if credibility_results and hasattr(credibility_results, 'evaluations'):
        source_metadata = credibility_results.source_metadata if hasattr(credibility_results, 'source_metadata') else {}
        
        for evaluation in credibility_results.evaluations:
            query_origin = url_to_query.get(evaluation.url, "")
            tier_lower = evaluation.credibility_tier.lower() if evaluation.credibility_tier else ""
            
            # Determine if credible (Tier 1 or Tier 2, score >= 0.70)
            is_credible = evaluation.credibility_score >= 0.70 and evaluation.recommended
            
            if is_credible:
                # Credible source
                credible = create_credible_source(evaluation, query_origin)
                
                # Add metadata if available
                if evaluation.url in source_metadata:
                    meta = source_metadata[evaluation.url]
                    credible.source_name = meta.name if hasattr(meta, 'name') else None
                    credible.source_type = meta.source_type if hasattr(meta, 'source_type') else None
                
                # Track scraping status
                credible.was_scraped = evaluation.url in scraped_urls
                if evaluation.url in scrape_errors:
                    credible.scrape_error = scrape_errors[evaluation.url]
                
                fact_audit.credible_sources.append(credible)
                
                # Update tier counts
                if "tier 1" in tier_lower:
                    fact_audit.tier1_count += 1
                else:
                    fact_audit.tier2_count += 1
            else:
                # Filtered source
                filtered = create_filtered_source(evaluation, query_origin)
                fact_audit.filtered_sources.append(filtered)
                fact_audit.tier3_filtered_count += 1
    
    return fact_audit


def build_session_search_audit(
    session_id: str,
    pipeline_type: str = "web_search",
    content_country: str = "international",
    content_language: str = "english"
) -> SessionSearchAudit:
    """
    Create a new SessionSearchAudit for a verification session
    
    Args:
        session_id: Unique session identifier
        pipeline_type: Type of pipeline (web_search, key_claims, llm_output)
        content_country: Detected country of the content
        content_language: Detected language of the content
    
    Returns:
        Empty SessionSearchAudit ready to receive fact audits
    """
    return SessionSearchAudit(
        session_id=session_id,
        pipeline_type=pipeline_type,
        content_country=content_country,
        content_language=content_language
    )


def save_search_audit(
    session_audit: SessionSearchAudit,
    file_manager,
    session_id: str,
    filename: str = "search_audit.json"
) -> str:
    """
    Save search audit to session directory
    
    Args:
        session_audit: The SessionSearchAudit to save
        file_manager: FileManager instance
        session_id: Session identifier
        filename: Name for the audit file
    
    Returns:
        Path to the saved file
    """
    try:
        audit_json = session_audit.to_json(indent=2)
        filepath = file_manager.save_session_file(
            session_id=session_id,
            filename=filename,
            content=audit_json,
            auto_serialize=False  # Already serialized
        )
        
        fact_logger.logger.info(
            f"📋 Saved search audit: {filename}",
            extra={
                "session_id": session_id,
                "total_facts": session_audit.total_facts,
                "total_sources": session_audit.total_credible_sources + session_audit.total_filtered_sources
            }
        )
        
        return filepath
        
    except Exception as e:
        fact_logger.logger.error(
            f"❌ Failed to save search audit: {e}",
            extra={"session_id": session_id, "error": str(e)}
        )
        raise


async def upload_search_audit_to_r2(
    session_audit: SessionSearchAudit,
    session_id: str,
    r2_uploader,
    pipeline_type: str = "web-search"
) -> Optional[str]:
    """
    Upload search audit to Cloudflare R2
    
    Args:
        session_audit: The SessionSearchAudit to upload
        session_id: Session identifier
        r2_uploader: R2Uploader instance
        pipeline_type: Type of pipeline for R2 folder structure
    
    Returns:
        R2 URL if successful, None otherwise
    """
    try:
        audit_json = session_audit.to_json(indent=2)
        
        # Create a temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(audit_json)
            temp_path = f.name
        
        try:
            # Upload to R2
            r2_filename = f"{pipeline_type}-audits/{session_id}/search_audit.json"
            
            url = r2_uploader.upload_file(
                file_path=temp_path,
                r2_filename=r2_filename,
                metadata={
                    'session-id': session_id,
                    'report-type': 'search-audit',
                    'pipeline-type': pipeline_type,
                    'total-facts': str(session_audit.total_facts),
                    'total-sources': str(session_audit.total_credible_sources)
                }
            )
            
            if url:
                fact_logger.logger.info(
                    f"☁️ Uploaded search audit to R2: {r2_filename}"
                )
            
            return url
            
        finally:
            # Clean up temp file
            os.unlink(temp_path)
            
    except Exception as e:
        fact_logger.logger.error(
            f"❌ Failed to upload search audit to R2: {e}",
            extra={"session_id": session_id, "error": str(e)}
        )
        return None
