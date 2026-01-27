# agents/report_synthesizer.py
"""
Report Synthesizer Agent
Stage 3: Comprehensive Analysis Synthesis

Analyzes all reports from Stage 1 and Stage 2 to create:
- Overall credibility score (0-100) and rating
- Cross-mode contradiction detection
- Categorized flags (credibility, bias, manipulation, factual accuracy)
- Key findings prioritized by importance
- Actionable recommendations
- Human-readable narrative summary

Uses GPT-4o for nuanced multi-report analysis.
"""

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
import json

from prompts.report_synthesizer_prompts import get_report_synthesizer_prompts
from utils.logger import fact_logger
from utils.langsmith_config import langsmith_config


# ============================================================================
# PYDANTIC OUTPUT MODELS
# ============================================================================

class Flag(BaseModel):
    """A credibility flag/concern"""
    severity: str = Field(
        description="Flag severity: critical, high, medium, low"
    )
    description: str = Field(
        description="Human-readable description of the concern"
    )
    source_mode: str = Field(
        description="Which analysis mode triggered this flag"
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Specific evidence supporting this flag"
    )


class Contradiction(BaseModel):
    """A contradiction found between analysis modes"""
    source_1: str = Field(
        description="First analysis mode"
    )
    finding_1: str = Field(
        description="Finding from first mode"
    )
    source_2: str = Field(
        description="Second analysis mode"
    )
    finding_2: str = Field(
        description="Contradicting finding from second mode"
    )
    explanation: str = Field(
        description="Why these findings contradict and what it means"
    )
    resolution_suggestion: Optional[str] = Field(
        default=None,
        description="Suggestion for resolving or interpreting the contradiction"
    )


class KeyFinding(BaseModel):
    """A key finding for readers"""
    finding: str = Field(
        description="The key finding in plain language"
    )
    importance: str = Field(
        description="Why this matters: critical, high, medium"
    )
    source_modes: List[str] = Field(
        default_factory=list,
        description="Which modes contributed to this finding"
    )
    supporting_evidence: Optional[List[str]] = Field(
        default=None,
        description="Brief evidence points supporting this finding"
    )


class SynthesisReport(BaseModel):
    """Complete synthesis report from Stage 3"""
    
    # Overall Assessment
    overall_credibility_score: float = Field(
        ge=0.0, le=100.0,
        description="Overall credibility score 0-100"
    )
    overall_credibility_rating: str = Field(
        description="Rating: Highly Credible, Credible, Mixed, Low Credibility, Unreliable"
    )
    confidence_in_assessment: float = Field(
        ge=0.0, le=100.0,
        description="How confident in this assessment 0-100"
    )
    
    # Score Breakdown
    score_breakdown: Dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of how score was calculated"
    )
    
    # Categorized Flags
    credibility_flags: List[Flag] = Field(
        default_factory=list,
        description="Flags related to source/author credibility"
    )
    bias_flags: List[Flag] = Field(
        default_factory=list,
        description="Flags related to political/framing bias"
    )
    manipulation_flags: List[Flag] = Field(
        default_factory=list,
        description="Flags related to manipulation techniques"
    )
    factual_accuracy_flags: List[Flag] = Field(
        default_factory=list,
        description="Flags related to factual accuracy issues"
    )
    
    # Contradictions
    contradictions: List[Contradiction] = Field(
        default_factory=list,
        description="Contradictions found between analysis modes"
    )
    
    # Key Findings
    key_findings: List[KeyFinding] = Field(
        default_factory=list,
        description="Top findings prioritized by importance"
    )
    
    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations for readers"
    )
    
    # Narrative Summary
    narrative_summary: str = Field(
        description="2-4 sentence conversational summary for general readers"
    )
    
    # Metadata
    modes_analyzed: List[str] = Field(
        default_factory=list,
        description="Which modes were analyzed"
    )
    modes_failed: List[str] = Field(
        default_factory=list,
        description="Which modes failed or had errors"
    )
    limitations: Optional[List[str]] = Field(
        default=None,
        description="Any limitations in the analysis"
    )


# ============================================================================
# REPORT SYNTHESIZER AGENT
# ============================================================================

class ReportSynthesizer:
    """
    Stage 3 Agent: Synthesizes all analysis reports into unified assessment
    
    Takes Stage 1 and Stage 2 results and produces:
    - Overall credibility score and rating
    - Categorized flags
    - Contradiction detection
    - Key findings
    - Recommendations
    - Narrative summary
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize LLM - GPT-4o for nuanced multi-report analysis
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0
        ).bind(response_format={"type": "json_object"})
        
        # Load prompts
        self.prompts = get_report_synthesizer_prompts()
        
        # Initialize parser
        self.parser = JsonOutputParser(pydantic_object=SynthesisReport)
        
        fact_logger.log_component_start(
            "ReportSynthesizer",
            model="gpt-4o"
        )
    
    def _format_content_classification(self, classification: Optional[Dict]) -> str:
        """Format content classification for prompt"""
        if not classification:
            return "Not available"
        
        return f"""
Content Type: {classification.get('content_type', 'Unknown')}
Realm: {classification.get('realm', 'Unknown')} / {classification.get('sub_realm', '')}
Purpose: {classification.get('purpose', 'Unknown')}
Contains References: {classification.get('contains_references', False)}
LLM Characteristics: {classification.get('llm_characteristics', {})}
"""
    
    def _format_source_verification(self, verification: Optional[Dict]) -> str:
        """Format source verification for prompt"""
        if not verification:
            return "Not available"
        
        if verification.get('error') or verification.get('status') == 'no_url_to_verify':
            return f"Source verification not performed: {verification.get('error', verification.get('status', 'Unknown'))}"
        
        return f"""
Domain: {verification.get('domain', 'Unknown')}
Credibility Tier: {verification.get('credibility_tier', 'Unknown')} - {verification.get('tier_description', '')}
Verification Source: {verification.get('verification_source', 'Unknown')}
Bias Rating: {verification.get('bias_rating', 'Unknown')}
Factual Reporting: {verification.get('factual_reporting', 'Unknown')}
Is Propaganda: {verification.get('is_propaganda', False)}
"""
    
    def _format_mode_routing(self, routing: Optional[Dict]) -> str:
        """Format mode routing for prompt"""
        if not routing:
            return "Not available"
        
        return f"""
Selected Modes: {', '.join(routing.get('selected_modes', []))}
Excluded Modes: {', '.join(routing.get('excluded_modes', []))}
Routing Reasoning: {routing.get('routing_reasoning', 'Not provided')}
Routing Confidence: {routing.get('routing_confidence', 'Unknown')}
"""
    
    def _format_mode_reports(self, mode_reports: Dict[str, Any], mode_errors: Dict[str, str]) -> str:
        """Format all mode reports for prompt"""
        sections = []
        
        # Key Claims Analysis
        if "key_claims_analysis" in mode_reports:
            kc = mode_reports["key_claims_analysis"]
            summary = kc.get("summary", {})
            claims = kc.get("key_claims", [])
            
            claims_detail = ""
            for i, claim in enumerate(claims[:5], 1):  # Limit to first 5
                verification = claim.get("verification", {})
                claims_detail += f"""
  Claim {i}: {claim.get('claim', 'N/A')[:200]}
    - Verdict: {verification.get('verdict', 'Unknown')}
    - Match Score: {verification.get('match_score', 0):.0%}
    - Sources: {len(verification.get('sources_used', []))}
"""
            
            sections.append(f"""
### Key Claims Analysis
Total Claims: {summary.get('total_key_claims', len(claims))}
Verified: {summary.get('verified_count', 0)}
Partially Verified: {summary.get('partial_count', 0)}
Unverified: {summary.get('unverified_count', 0)}
Average Confidence: {summary.get('average_confidence', 0):.0%}
Overall Credibility: {summary.get('overall_credibility', 'Unknown')}

Top Claims:{claims_detail}
""")
        elif "key_claims_analysis" in mode_errors:
            sections.append(f"### Key Claims Analysis\nFAILED: {mode_errors['key_claims_analysis']}")
        
        # Bias Analysis
        if "bias_analysis" in mode_reports:
            bias = mode_reports["bias_analysis"]
            analysis = bias.get("analysis", {})
            
            sections.append(f"""
### Bias Analysis
Consensus Bias Score: {analysis.get('consensus_bias_score', 0)}/10 ({analysis.get('consensus_direction', 'Unknown')})
Confidence: {analysis.get('confidence', 0):.0%}
GPT Assessment: {analysis.get('gpt_analysis', {}).get('political_lean', 'Unknown')}
Claude Assessment: {analysis.get('claude_analysis', {}).get('political_lean', 'Unknown')}
Final Assessment: {analysis.get('final_assessment', 'Not provided')[:500]}
Areas of Agreement: {', '.join(analysis.get('areas_of_agreement', [])[:3])}
Areas of Disagreement: {', '.join(analysis.get('areas_of_disagreement', [])[:3])}
""")
        elif "bias_analysis" in mode_errors:
            sections.append(f"### Bias Analysis\nFAILED: {mode_errors['bias_analysis']}")
        
        # Manipulation Detection
        if "manipulation_detection" in mode_reports:
            manip = mode_reports["manipulation_detection"]
            report = manip.get("report", {})
            
            techniques = report.get("techniques_used", manip.get("techniques_used", []))
            
            sections.append(f"""
### Manipulation Detection
Manipulation Score: {manip.get('manipulation_score', 0)}/10
Score Justification: {report.get('justification', manip.get('score_justification', 'Not provided'))[:500]}
Techniques Used: {', '.join(techniques[:5]) if techniques else 'None detected'}
Narrative Summary: {report.get('narrative_summary', manip.get('narrative_summary', 'Not provided'))[:500]}
What Article Got Right: {', '.join(report.get('what_article_got_right', [])[:3])}
Key Misleading Elements: {', '.join(report.get('key_misleading_elements', [])[:3])}
""")
        elif "manipulation_detection" in mode_errors:
            sections.append(f"### Manipulation Detection\nFAILED: {mode_errors['manipulation_detection']}")
        
        # Lie Detection
        if "lie_detection" in mode_reports:
            lie = mode_reports["lie_detection"]
            
            sections.append(f"""
### Lie Detection (Linguistic Analysis)
Deception Likelihood Score: {lie.get('deception_likelihood_score', lie.get('overall_score', 0))}/10
Overall Assessment: {lie.get('overall_assessment', 'Unknown')}
Markers Found: {lie.get('markers_found', 0)}
Key Linguistic Findings: {lie.get('key_findings', 'Not provided')[:500] if isinstance(lie.get('key_findings'), str) else ', '.join(lie.get('key_findings', [])[:3])}
""")
        elif "lie_detection" in mode_errors:
            sections.append(f"### Lie Detection\nFAILED: {mode_errors['lie_detection']}")
        
        # LLM Output Verification
        if "llm_output_verification" in mode_reports:
            llm = mode_reports["llm_output_verification"]
            
            sections.append(f"""
### LLM Output Verification
Total Claims: {llm.get('total_claims', 0)}
Verified Count: {llm.get('verified_count', 0)}
Interpretation Accuracy: {llm.get('interpretation_accuracy', 0):.0%}
Sources Checked: {llm.get('sources_checked', 0)}
""")
        elif "llm_output_verification" in mode_errors:
            sections.append(f"### LLM Output Verification\nFAILED: {mode_errors['llm_output_verification']}")
        
        return "\n".join(sections) if sections else "No mode reports available"
    
    @traceable(
        name="synthesize_reports",
        run_type="chain",
        tags=["report-synthesizer", "stage3", "gpt-4o"]
    )
    async def synthesize(
        self,
        stage1_results: Dict[str, Any],
        stage2_results: Dict[str, Any]
    ) -> SynthesisReport:
        """
        Synthesize all analysis reports into unified assessment
        
        Args:
            stage1_results: Results from Stage 1 (classification, verification, routing)
            stage2_results: Results from Stage 2 (mode_reports, mode_errors)
            
        Returns:
            SynthesisReport with complete unified assessment
        """
        start_time = time.time()
        
        # Extract data
        content_classification = stage1_results.get("content_classification")
        source_verification = stage1_results.get("source_verification")
        mode_routing = stage1_results.get("mode_routing")
        
        mode_reports = stage2_results.get("mode_reports", {})
        mode_errors = stage2_results.get("mode_errors", {})
        
        fact_logger.logger.info(
            "🔬 Stage 3: Synthesizing reports",
            extra={
                "modes_completed": list(mode_reports.keys()),
                "modes_failed": list(mode_errors.keys())
            }
        )
        
        # Format inputs for prompt
        content_classification_str = self._format_content_classification(content_classification)
        source_verification_str = self._format_source_verification(source_verification)
        mode_routing_str = self._format_mode_routing(mode_routing)
        mode_reports_str = self._format_mode_reports(mode_reports, mode_errors)
        
        # Build prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.prompts["system"]),
            ("user", self.prompts["user"])
        ])
        
        prompt_with_format = prompt.partial(
            format_instructions=self.parser.get_format_instructions()
        )
        
        # Execute chain
        callbacks = langsmith_config.get_callbacks("report_synthesis")
        chain = prompt_with_format | self.llm | self.parser
        
        try:
            response = await chain.ainvoke(
                {
                    "content_classification": content_classification_str,
                    "source_verification": source_verification_str,
                    "mode_routing": mode_routing_str,
                    "mode_reports_formatted": mode_reports_str
                },
                config={"callbacks": callbacks}
            )
            
            # Add metadata
            response["modes_analyzed"] = list(mode_reports.keys())
            response["modes_failed"] = list(mode_errors.keys())
            
            # Validate and create report
            synthesis_report = SynthesisReport(**response)
            
            duration = time.time() - start_time
            fact_logger.logger.info(
                "✅ Stage 3 synthesis complete",
                extra={
                    "duration": round(duration, 2),
                    "overall_score": synthesis_report.overall_credibility_score,
                    "overall_rating": synthesis_report.overall_credibility_rating,
                    "flags_count": (
                        len(synthesis_report.credibility_flags) +
                        len(synthesis_report.bias_flags) +
                        len(synthesis_report.manipulation_flags) +
                        len(synthesis_report.factual_accuracy_flags)
                    ),
                    "contradictions_count": len(synthesis_report.contradictions),
                    "key_findings_count": len(synthesis_report.key_findings)
                }
            )
            
            return synthesis_report
            
        except Exception as e:
            fact_logger.logger.error(f"❌ Report synthesis failed: {e}")
            
            # Return a fallback synthesis report on error
            return self._create_fallback_report(
                mode_reports, 
                mode_errors, 
                str(e)
            )
    
    def _create_fallback_report(
        self,
        mode_reports: Dict[str, Any],
        mode_errors: Dict[str, str],
        error_message: str
    ) -> SynthesisReport:
        """Create a basic fallback synthesis report when AI synthesis fails"""
        
        # Calculate basic metrics from available data
        flags = []
        score = 50.0  # Start neutral
        
        # Check key claims if available
        if "key_claims_analysis" in mode_reports:
            kc = mode_reports["key_claims_analysis"]
            summary = kc.get("summary", {})
            avg_conf = summary.get("average_confidence", 0.5)
            
            if avg_conf < 0.4:
                score -= 20
                flags.append(Flag(
                    severity="high",
                    description=f"Low fact verification confidence ({avg_conf:.0%})",
                    source_mode="key_claims_analysis"
                ))
        
        # Check bias if available
        if "bias_analysis" in mode_reports:
            bias = mode_reports["bias_analysis"]
            analysis = bias.get("analysis", {})
            bias_score = abs(analysis.get("consensus_bias_score", 0))
            
            if bias_score > 6:
                score -= 15
                direction = analysis.get("consensus_direction", "Unknown")
                flags.append(Flag(
                    severity="medium",
                    description=f"Significant {direction} bias detected (score: {bias_score:.1f}/10)",
                    source_mode="bias_analysis"
                ))
        
        # Check manipulation if available
        if "manipulation_detection" in mode_reports:
            manip = mode_reports["manipulation_detection"]
            manip_score = manip.get("manipulation_score", 0)
            
            if manip_score > 6:
                score -= 20
                flags.append(Flag(
                    severity="high",
                    description=f"High manipulation score ({manip_score:.1f}/10)",
                    source_mode="manipulation_detection"
                ))
        
        # Determine rating
        if score >= 70:
            rating = "Credible"
        elif score >= 50:
            rating = "Mixed"
        elif score >= 30:
            rating = "Low Credibility"
        else:
            rating = "Unreliable"
        
        return SynthesisReport(
            overall_credibility_score=max(0, min(100, score)),
            overall_credibility_rating=rating,
            confidence_in_assessment=40.0,  # Low confidence due to fallback
            score_breakdown={"note": "Fallback calculation due to synthesis error"},
            credibility_flags=[f for f in flags if "credibility" in f.source_mode.lower()],
            bias_flags=[f for f in flags if "bias" in f.source_mode.lower()],
            manipulation_flags=[f for f in flags if "manipulation" in f.source_mode.lower()],
            factual_accuracy_flags=[f for f in flags if "claims" in f.source_mode.lower()],
            contradictions=[],
            key_findings=[
                KeyFinding(
                    finding="Analysis completed with basic metrics. Full AI synthesis unavailable.",
                    importance="medium",
                    source_modes=list(mode_reports.keys())
                )
            ],
            recommendations=[
                "Review the individual mode reports for detailed findings",
                "Consider re-running the analysis if this issue persists"
            ],
            narrative_summary=f"Analysis completed but full synthesis was unavailable. Based on basic metrics, this content has {rating.lower()} credibility. Please review the individual analysis sections for detailed findings.",
            modes_analyzed=list(mode_reports.keys()),
            modes_failed=list(mode_errors.keys()),
            limitations=[f"AI synthesis failed: {error_message}"]
        )


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test():
        synthesizer = ReportSynthesizer()
        
        # Mock Stage 1 results
        stage1_results = {
            "content_classification": {
                "content_type": "news_article",
                "realm": "politics",
                "sub_realm": "domestic_policy",
                "purpose": "inform"
            },
            "source_verification": {
                "domain": "example.com",
                "credibility_tier": 2,
                "tier_description": "Generally reliable source",
                "bias_rating": "left-center"
            },
            "mode_routing": {
                "selected_modes": ["key_claims_analysis", "bias_analysis"],
                "excluded_modes": ["llm_output_verification"]
            }
        }
        
        # Mock Stage 2 results
        stage2_results = {
            "mode_reports": {
                "key_claims_analysis": {
                    "summary": {
                        "total_key_claims": 5,
                        "verified_count": 3,
                        "partial_count": 1,
                        "unverified_count": 1,
                        "average_confidence": 0.72,
                        "overall_credibility": "Mostly Credible"
                    },
                    "key_claims": [
                        {
                            "claim": "The policy was enacted in 2023",
                            "verification": {"verdict": "Verified", "match_score": 0.95}
                        }
                    ]
                },
                "bias_analysis": {
                    "analysis": {
                        "consensus_bias_score": 3.5,
                        "consensus_direction": "Left-leaning",
                        "confidence": 0.75,
                        "final_assessment": "Moderate left bias detected in framing"
                    }
                }
            },
            "mode_errors": {}
        }
        
        result = await synthesizer.synthesize(stage1_results, stage2_results)
        
        print("\n" + "="*60)
        print("SYNTHESIS REPORT")
        print("="*60)
        print(f"Overall Score: {result.overall_credibility_score}/100")
        print(f"Rating: {result.overall_credibility_rating}")
        print(f"Confidence: {result.confidence_in_assessment}%")
        print(f"\nNarrative Summary:\n{result.narrative_summary}")
        print(f"\nKey Findings: {len(result.key_findings)}")
        for finding in result.key_findings:
            print(f"  - [{finding.importance}] {finding.finding}")
        print(f"\nRecommendations: {len(result.recommendations)}")
        for rec in result.recommendations:
            print(f"  - {rec}")
        print(f"\nFlags raised:")
        print(f"  Credibility: {len(result.credibility_flags)}")
        print(f"  Bias: {len(result.bias_flags)}")
        print(f"  Manipulation: {len(result.manipulation_flags)}")
        print(f"  Factual Accuracy: {len(result.factual_accuracy_flags)}")
        print(f"\nContradictions: {len(result.contradictions)}")
    
    asyncio.run(test())
