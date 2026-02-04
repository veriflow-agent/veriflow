# utils/metadata_block.py
"""
Metadata Block - Standardized building block for comprehensive analysis

Every pre-analysis check (content classification, source credibility, author
investigation, date freshness, etc.) produces a MetadataBlock. The synthesizer
and fallback scoring consume these blocks generically, so adding a new check
requires zero changes to the synthesis pipeline.

Each block is responsible for:
1. Storing its raw data
2. Providing a human-readable summary for the LLM synthesizer
3. Providing structured impact signals for fallback scoring
4. Providing a display-ready dict for the frontend
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ImpactSignal(BaseModel):
    """
    Structured signal that a metadata block provides for fallback scoring.
    
    When AI synthesis fails, the fallback scorer iterates over all blocks,
    collects their impact signals, and computes a mechanical score.
    """
    
    # Score adjustments (applied additively to a base score of 50)
    score_adjustment: int = Field(
        default=0,
        description="Points to add/subtract from credibility score (-30 to +30)"
    )
    
    # Flags for the fallback report
    flags: List[str] = Field(
        default_factory=list,
        description="Warning flags to surface (e.g., 'Propaganda source detected')"
    )
    flag_severity: str = Field(
        default="medium",
        description="Severity of flags: low, medium, high"
    )
    flag_category: str = Field(
        default="credibility",
        description="Category: credibility, bias, factual_accuracy, manipulation"
    )
    
    # Positive indicators
    positives: List[str] = Field(
        default_factory=list,
        description="Positive credibility indicators"
    )


class MetadataBlock(BaseModel):
    """
    A single pre-analysis result, packaged for the synthesis pipeline.
    
    Every Stage 1 check produces one of these. The synthesizer collects all
    blocks and feeds them to the LLM as context, without needing to know
    what specific checks exist.
    """
    
    # Identity
    block_type: str = Field(
        description="Unique identifier: content_classification, source_credibility, "
                     "author_investigation, date_freshness, etc."
    )
    display_name: str = Field(
        description="Human-readable name for UI display (e.g., 'Source Credibility')"
    )
    
    # The raw data from the check (preserved for frontend rendering & audit)
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full raw results from the check"
    )
    
    # Pre-formatted text for the LLM synthesizer prompt
    # Each block formats ITSELF -- the synthesizer doesn't need to know how
    summary_for_synthesis: str = Field(
        default="No data available",
        description="Human-readable summary for the LLM synthesis prompt"
    )
    
    # Structured signals for fallback scoring (when AI synthesis fails)
    impact: ImpactSignal = Field(
        default_factory=ImpactSignal,
        description="Structured signals for mechanical/fallback scoring"
    )
    
    # Status
    success: bool = Field(
        default=True,
        description="Whether this check completed successfully"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if check failed"
    )
    
    # Processing metadata
    processing_time_ms: int = Field(
        default=0,
        description="How long this check took in milliseconds"
    )

    def to_frontend_dict(self) -> Dict[str, Any]:
        """
        Returns data shaped for frontend rendering.
        
        The frontend iterates over metadata blocks and renders each one
        using block_type to pick the right renderer.
        """
        return {
            "block_type": self.block_type,
            "display_name": self.display_name,
            "data": self.data,
            "success": self.success,
            "error": self.error,
        }


# =============================================================================
# BUILDER FUNCTIONS
# =============================================================================
# These wrap existing check outputs into MetadataBlocks.
# Each new check only needs to add one builder function here.

def build_content_classification_block(
    classification_data: Dict[str, Any],
    success: bool = True,
    error: Optional[str] = None,
    processing_time_ms: int = 0
) -> MetadataBlock:
    """
    Wrap ContentClassifier output into a MetadataBlock.
    
    Args:
        classification_data: The .model_dump() output from ContentClassification
        success: Whether classification succeeded
        error: Error message if it failed
        processing_time_ms: Processing time
    
    Returns:
        MetadataBlock ready for the synthesis pipeline
    """
    if not success or not classification_data or classification_data.get("error"):
        return MetadataBlock(
            block_type="content_classification",
            display_name="Content Classification",
            data=classification_data or {},
            summary_for_synthesis="Content classification was not available.",
            impact=ImpactSignal(),
            success=False,
            error=error or classification_data.get("error", "Classification failed"),
            processing_time_ms=processing_time_ms,
        )
    
    content_type = classification_data.get("content_type", "unknown")
    realm = classification_data.get("realm", "unknown")
    sub_realm = classification_data.get("sub_realm", "")
    purpose = classification_data.get("apparent_purpose", "unknown")
    language = classification_data.get("detected_language", "unknown")
    country = classification_data.get("detected_country", "")
    is_llm = classification_data.get("is_likely_llm_output", False)
    formality = classification_data.get("formality_level", "unknown")
    ref_count = classification_data.get("reference_count", 0)
    llm_indicators = classification_data.get("llm_output_indicators", [])
    notable = classification_data.get("notable_characteristics", [])
    
    # Build synthesis summary
    realm_str = f"{realm} / {sub_realm}" if sub_realm else realm
    lines = [
        f"Content Type: {content_type}",
        f"Topic/Realm: {realm_str}",
        f"Apparent Purpose: {purpose}",
        f"Language: {language}",
        f"Formality: {formality}",
    ]
    if country:
        lines.append(f"Geographic Focus: {country}")
    if is_llm:
        lines.append(f"AI-Generated Content: Yes (indicators: {', '.join(llm_indicators[:3])})")
    if ref_count > 0:
        lines.append(f"Source References Found: {ref_count}")
    if notable:
        lines.append(f"Notable Features: {', '.join(notable[:3])}")
    
    summary = "\n".join(lines)
    
    # Build impact signals
    impact = ImpactSignal()
    
    # Opinion content should be scored differently
    if content_type in ("opinion_column", "blog_post", "advertisement", "satire"):
        impact.flags.append(
            f"Content is {content_type.replace('_', ' ')} -- bias and persuasion "
            f"are expected for this format"
        )
        impact.flag_severity = "low"
        impact.flag_category = "credibility"
    
    if purpose in ("persuade", "advocate", "advertise"):
        impact.flags.append(f"Content purpose is to {purpose} -- not neutral reporting")
        impact.flag_severity = "medium"
        impact.flag_category = "credibility"
    
    if is_llm:
        impact.flags.append("Content appears to be AI-generated")
        impact.flag_severity = "medium"
        impact.flag_category = "credibility"
    
    # Positive: formal news articles from factual realms
    if content_type == "news_article" and formality == "formal":
        impact.positives.append("Formal news article format")
    
    if content_type == "academic_paper":
        impact.positives.append("Academic/research format")
        impact.score_adjustment = 5
    
    return MetadataBlock(
        block_type="content_classification",
        display_name="Content Classification",
        data=classification_data,
        summary_for_synthesis=summary,
        impact=impact,
        success=True,
        processing_time_ms=processing_time_ms,
    )


def build_source_credibility_block(
    verification_data: Dict[str, Any],
    success: bool = True,
    error: Optional[str] = None,
    processing_time_ms: int = 0
) -> MetadataBlock:
    """
    Wrap SourceVerifier output into a MetadataBlock.
    
    Args:
        verification_data: Dict from source verification step
        success: Whether verification succeeded
        error: Error message if it failed
        processing_time_ms: Processing time
    
    Returns:
        MetadataBlock ready for the synthesis pipeline
    """
    # Handle "no URL to verify" case
    if not verification_data or verification_data.get("status") == "no_url_to_verify":
        return MetadataBlock(
            block_type="source_credibility",
            display_name="Source Credibility",
            data=verification_data or {},
            summary_for_synthesis=(
                "Source credibility could not be assessed: no URL was provided. "
                "This limits our ability to evaluate the publication's track record."
            ),
            impact=ImpactSignal(
                flags=["No source URL provided -- cannot verify publication credibility"],
                flag_severity="medium",
                flag_category="credibility",
            ),
            success=False,
            error="No URL to verify",
            processing_time_ms=processing_time_ms,
        )
    
    # Handle verification failure
    if verification_data.get("error") or not success:
        return MetadataBlock(
            block_type="source_credibility",
            display_name="Source Credibility",
            data=verification_data,
            summary_for_synthesis=(
                f"Source credibility check failed: "
                f"{verification_data.get('error', 'Unknown error')}. "
                f"Could not determine publication reliability."
            ),
            impact=ImpactSignal(),
            success=False,
            error=error or verification_data.get("error", "Verification failed"),
            processing_time_ms=processing_time_ms,
        )
    
    # Successful verification
    domain = verification_data.get("domain", "Unknown")
    tier = verification_data.get("credibility_tier", 3)
    tier_desc = verification_data.get("tier_description", "")
    bias_rating = verification_data.get("bias_rating", "Unknown")
    factual = verification_data.get("factual_reporting", "Unknown")
    is_propaganda = verification_data.get("is_propaganda", False)
    verification_source = verification_data.get("verification_source", "Unknown")
    
    # Build synthesis summary
    lines = [
        f"Domain: {domain}",
        f"Credibility Tier: {tier} - {tier_desc}",
        f"Verification Source: {verification_source}",
        f"Bias Rating: {bias_rating}",
        f"Factual Reporting: {factual}",
    ]
    if is_propaganda:
        lines.append("WARNING: Source is flagged as propaganda")
    
    summary = "\n".join(lines)
    
    # Build impact signals
    impact = ImpactSignal()
    
    if tier == 1:
        impact.score_adjustment = 15
        impact.positives.append(
            f"Source ({domain}) is Tier 1 -- highly credible "
            f"(verified via {verification_source})"
        )
    elif tier == 2:
        impact.score_adjustment = 8
        impact.positives.append(
            f"Source ({domain}) is Tier 2 -- credible with strong factual reporting"
        )
    elif tier == 4:
        impact.score_adjustment = -15
        impact.flags.append(
            f"Source ({domain}) has low credibility (Tier {tier})"
        )
        impact.flag_severity = "high"
        impact.flag_category = "credibility"
    elif tier >= 5:
        impact.score_adjustment = -25
        impact.flags.append(
            f"Source ({domain}) is unreliable (Tier {tier}) -- "
            f"known for poor factual reporting"
        )
        impact.flag_severity = "high"
        impact.flag_category = "credibility"
    
    if is_propaganda:
        impact.score_adjustment = min(impact.score_adjustment, -20)
        impact.flags.append(f"Source ({domain}) is flagged as propaganda")
        impact.flag_severity = "high"
        impact.flag_category = "credibility"
    
    # Bias note (informational, not necessarily a penalty)
    if bias_rating and bias_rating.upper() in ("FAR-LEFT", "FAR-RIGHT"):
        impact.flags.append(
            f"Source has extreme bias rating: {bias_rating}"
        )
        impact.flag_severity = "medium"
        impact.flag_category = "bias"
        impact.score_adjustment -= 5
    
    return MetadataBlock(
        block_type="source_credibility",
        display_name="Source Credibility",
        data=verification_data,
        summary_for_synthesis=summary,
        impact=impact,
        success=True,
        processing_time_ms=processing_time_ms,
    )
