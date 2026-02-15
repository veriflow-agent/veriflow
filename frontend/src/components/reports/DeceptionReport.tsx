// src/components/reports/DeceptionReport.tsx
import { cn } from "@/lib/utils";
import { RiskBadge, SessionInfo, ScoreBadge } from "./shared";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

// Backend MarkerCategory model fields:
//   category (str), present (bool), severity (str),
//   examples (List[str]), explanation (str)
type Marker = {
  category: string;          // was marker_name
  present: boolean;
  severity?: string | null;
  explanation?: string | null; // was description
  examples?: string[];
};

type Props = {
  data: {
    analysis?: {
      credibility_score?: number;
      risk_level?: string;
      overall_assessment?: string;
      markers_detected?: Marker[];
      positive_indicators?: string[];
      conclusion?: string;
      reasoning?: string;
    };
    session_id?: string;
    processing_time?: number;
  };
};

const severityColor = (s?: string | null) => {
  switch (s?.toLowerCase()) {
    case "low": return "bg-score-high/15 text-score-high";
    case "moderate":
    case "medium": return "bg-score-moderate/15 text-score-moderate";
    case "high": return "bg-score-low/15 text-score-low";
    default: return "bg-muted text-muted-foreground";
  }
};

const DeceptionReport = ({ data }: Props) => {
  const [showReasoning, setShowReasoning] = useState(false);
  const a = data.analysis;
  const score = a?.credibility_score ?? 0;
  const activeMarkers = a?.markers_detected?.filter(m => m.present) || [];
  const credIndicators = a?.markers_detected?.filter(m => !m.present) || [];

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-xl font-display font-semibold mb-1">Deception Detection</h3>
        <p className="text-sm text-muted-foreground mb-4">
          We analyze linguistic patterns commonly associated with misleading communication.
        </p>

        <div className="flex items-center gap-4 mb-4">
          <RiskBadge level={a?.risk_level || "unknown"} />
          <ScoreBadge score={score} label="Credibility" />
        </div>

        {a?.overall_assessment && (
          <p className="text-base leading-relaxed mb-4">{a.overall_assessment}</p>
        )}

        {activeMarkers.length > 0 && (
          <div className="space-y-2 mb-4">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Deception Markers Found
            </h4>
            {activeMarkers.map((m, i) => (
              <div key={i} className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base font-medium">{m.category}</span>
                  <span className={cn("rounded px-1.5 py-0.5 text-xs font-semibold uppercase", severityColor(m.severity))}>
                    {m.severity}
                  </span>
                </div>
                {m.explanation && <p className="text-sm text-muted-foreground">{m.explanation}</p>}
                {m.examples?.map((ex, j) => (
                  <p key={j} className="text-sm text-muted-foreground mt-1 pl-3 border-l-2 border-border italic">
                    {ex}
                  </p>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Positive indicators from backend */}
        {a?.positive_indicators && a.positive_indicators.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Credibility Indicators
            </h4>
            <div className="space-y-1">
              {a.positive_indicators.map((ind, i) => (
                <p key={i} className="text-sm text-muted-foreground pl-3 border-l-2 border-score-high">
                  {ind}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Inactive markers as reasoning detail */}
        {credIndicators.length > 0 && (
          <div>
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              View Detailed Reasoning {showReasoning ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showReasoning && (
              <div className="mt-2 space-y-1">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Markers Not Detected
                </h4>
                {credIndicators.map((m, i) => (
                  <p key={i} className="text-sm text-muted-foreground">
                    {m.category}
                  </p>
                ))}
                {a?.reasoning && (
                  <p className="text-sm text-muted-foreground mt-2 pt-2 border-t border-border">
                    {a.reasoning}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default DeceptionReport;