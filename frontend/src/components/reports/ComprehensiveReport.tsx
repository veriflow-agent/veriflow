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
    synthesis_report?: {
      overall_score?: number;
      overall_rating?: string;
      confidence?: number;
      summary?: string;
      key_concerns?: string[];
      positive_indicators?: string[];
      recommendations?: string[];
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

const ComprehensiveReport = ({ data }: Props) => {
  const [expandedModes, setExpandedModes] = useState<Record<string, boolean>>({});
  const synth = data.synthesis_report;
  const score = synth?.overall_score ?? 0;

  const toggleMode = (mode: string) => {
    setExpandedModes(prev => ({ ...prev, [mode]: !prev[mode] }));
  };

  const renderSubReport = (modeKey: string, modeData: any) => {
    switch (modeKey) {
      case "key_claims": return <KeyClaimsReport data={modeData} />;
      case "bias_check": return <BiasReport data={modeData} />;
      case "lie_detection": return <DeceptionReport data={modeData} />;
      case "manipulation_check": return <ManipulationReport data={modeData} />;
      default: return <pre className="text-xs overflow-auto">{JSON.stringify(modeData, null, 2)}</pre>;
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
          {data.source_verification?.credibility_tier && (
            <div className={cn("rounded-lg px-3 py-1.5 text-xs font-medium", tierColors[data.source_verification.credibility_tier])}>
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
      </div>

      {/* Mode Reports */}
      {data.mode_reports && Object.entries(data.mode_reports).map(([key, value]) => (
        <div key={key} className="rounded-xl border border-border bg-card overflow-hidden">
          <button
            onClick={() => toggleMode(key)}
            className="w-full flex items-center justify-between p-4 text-sm font-medium hover:bg-secondary/50 transition-colors"
          >
            <span className="capitalize">{key.replace("_", " ")}</span>
            {expandedModes[key] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {expandedModes[key] && (
            <div className="px-4 pb-4">
              {renderSubReport(key, value)}
            </div>
          )}
        </div>
      ))}

      {/* Synthesis */}
      {synth && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-lg font-display font-semibold mb-3">Overall Assessment</h3>

          <div className="flex items-center gap-4 mb-4">
            <ScoreBadge score={score} label={synth.overall_rating || getScoreLabel(score)} />
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
