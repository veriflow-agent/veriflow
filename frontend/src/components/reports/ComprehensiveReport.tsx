// src/components/reports/ComprehensiveReport.tsx
import { cn } from "@/lib/utils";
import { ScoreBadge, SessionInfo, getScoreColor, getScoreLabel } from "./shared";
import KeyClaimsReport from "./KeyClaimsReport";
import BiasReport from "./BiasReport";
import DeceptionReport from "./DeceptionReport";
import ManipulationReport from "./ManipulationReport";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

type Props = {
  data: {
    content_classification?: Record<string, any>;
    source_verification?: Record<string, any>;
    mode_routing?: { selected_modes?: string[]; reasoning?: string };
    mode_reports?: Record<string, any>;
    mode_errors?: Record<string, string>;
    synthesis_report?: {
      overall_score?: number;
      overall_rating?: string;
      overall_credibility_score?: number;  // alternate field name
      overall_credibility_rating?: string; // alternate field name
      confidence?: number;
      summary?: string;
      key_concerns?: string[];
      positive_indicators?: string[];
      recommendations?: string[];
      modes_analyzed?: string[];
    };
    session_id?: string;
    processing_time?: number;
  };
};

const tierColors: Record<number, string> = {
  1: "bg-score-high text-accent-foreground",
  2: "bg-tier-2 text-accent-foreground",
  3: "bg-score-moderate text-foreground",
  4: "bg-score-elevated text-accent-foreground",
  5: "bg-score-low text-accent-foreground",
};

// Backend mode IDs -> display names
const modeLabels: Record<string, string> = {
  key_claims_analysis: "Key Claims Verification",
  bias_analysis: "Bias Analysis",
  manipulation_detection: "Manipulation Detection",
  lie_detection: "Deception Detection",
  llm_output_verification: "LLM Output Verification",
};

const ComprehensiveReport = ({ data }: Props) => {
  const [expandedModes, setExpandedModes] = useState<Record<string, boolean>>({});
  const synth = data.synthesis_report;
  // Handle both field name variants
  const score = synth?.overall_score ?? synth?.overall_credibility_score ?? 0;
  const rating = synth?.overall_rating ?? synth?.overall_credibility_rating;

  const toggleMode = (mode: string) => {
    setExpandedModes(prev => ({ ...prev, [mode]: !prev[mode] }));
  };

  // Map backend mode IDs to the correct sub-report component
  // Backend uses: key_claims_analysis, bias_analysis, manipulation_detection, lie_detection
  const renderSubReport = (modeKey: string, modeData: any) => {
    switch (modeKey) {
      case "key_claims_analysis":
        return <KeyClaimsReport data={modeData} />;
      case "bias_analysis":
        return <BiasReport data={modeData} />;
      case "lie_detection":
        return <DeceptionReport data={modeData} />;
      case "manipulation_detection":
        return <ManipulationReport data={modeData} />;
      case "llm_output_verification":
        // Fallback to JSON for now
        return <pre className="text-xs overflow-auto">{JSON.stringify(modeData, null, 2)}</pre>;
      default:
        return <pre className="text-xs overflow-auto">{JSON.stringify(modeData, null, 2)}</pre>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Metadata Panel */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-display font-semibold mb-3">Comprehensive Analysis</h3>

        <div className="flex flex-wrap gap-4 mb-3">
          {data.content_classification?.content_type && (
            <div className="rounded-lg bg-secondary px-3 py-1.5 text-xs">
              <span className="text-muted-foreground">Type:</span>{" "}
              <span className="font-medium capitalize">{data.content_classification.content_type.replace("_", " ")}</span>
            </div>
          )}
          {data.content_classification?.realm && (
            <div className="rounded-lg bg-secondary px-3 py-1.5 text-xs">
              <span className="text-muted-foreground">Realm:</span>{" "}
              <span className="font-medium capitalize">{data.content_classification.realm}</span>
            </div>
          )}
          {data.source_verification?.credibility_tier && (
            <div className={cn("rounded-lg px-3 py-1.5 text-xs font-medium", tierColors[data.source_verification.credibility_tier] || "bg-muted")}>
              Tier {data.source_verification.credibility_tier} - {data.source_verification.publication_name}
            </div>
          )}
          {data.source_verification?.bias_rating && (
            <div className="rounded-lg bg-secondary px-3 py-1.5 text-xs">
              <span className="text-muted-foreground">Bias:</span>{" "}
              <span className="font-medium">{data.source_verification.bias_rating}</span>
            </div>
          )}
        </div>

        {/* Mode routing info */}
        {data.mode_routing?.selected_modes && (
          <p className="text-xs text-muted-foreground">
            Modes selected: {data.mode_routing.selected_modes.map(m => modeLabels[m] || m).join(", ")}
          </p>
        )}
      </div>

      {/* Mode Reports */}
      {data.mode_reports && Object.entries(data.mode_reports).map(([key, value]) => (
        <div key={key} className="rounded-xl border border-border bg-card overflow-hidden">
          <button
            onClick={() => toggleMode(key)}
            className="w-full flex items-center justify-between p-4 text-sm font-medium hover:bg-secondary/50 transition-colors"
          >
            <span>{modeLabels[key] || key.replace(/_/g, " ")}</span>
            {expandedModes[key] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {expandedModes[key] && (
            <div className="px-4 pb-4">
              {renderSubReport(key, value)}
            </div>
          )}
        </div>
      ))}

      {/* Mode Errors */}
      {data.mode_errors && Object.keys(data.mode_errors).length > 0 && (
        <div className="rounded-xl border border-score-low/30 bg-score-low/5 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-score-low mb-2">
            Failed Modes
          </h4>
          {Object.entries(data.mode_errors).map(([key, err]) => (
            <p key={key} className="text-xs text-muted-foreground">
              {modeLabels[key] || key}: {err}
            </p>
          ))}
        </div>
      )}

      {/* Synthesis */}
      {synth && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-lg font-display font-semibold mb-3">Overall Assessment</h3>

          <div className="flex items-center gap-4 mb-4">
            <ScoreBadge score={score} label={rating || getScoreLabel(score)} />
            {synth.confidence != null && (
              <span className="text-xs text-muted-foreground">Confidence: {Math.round(synth.confidence)}%</span>
            )}
          </div>

          {synth.summary && <p className="text-sm leading-relaxed mb-4">{synth.summary}</p>}

          {synth.key_concerns?.length ? (
            <div className="mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Key Concerns</h4>
              <ul className="space-y-1">
                {synth.key_concerns.map((c, i) => (
                  <li key={i} className="text-xs text-muted-foreground pl-3 border-l-2 border-score-low">{c}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {synth.positive_indicators?.length ? (
            <div className="mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Positive Indicators</h4>
              <ul className="space-y-1">
                {synth.positive_indicators.map((p, i) => (
                  <li key={i} className="text-xs text-muted-foreground pl-3 border-l-2 border-score-high">{p}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {synth.recommendations?.length ? (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Recommendations</h4>
              <ul className="space-y-1">
                {synth.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-muted-foreground pl-3 border-l-2 border-border">{r}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}

      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default ComprehensiveReport;
