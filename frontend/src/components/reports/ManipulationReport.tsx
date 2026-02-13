// src/components/reports/ManipulationReport.tsx
import { cn } from "@/lib/utils";
import { SessionInfo, getScoreColor } from "./shared";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

type Props = {
  data: {
    manipulation_score?: number;
    report?: {
      justification?: string;
      narrative_summary?: string;
      techniques_detected?: { technique: string; severity: string; description: string; evidence?: string[]; fact_check?: string }[];
      factual_distortions?: { original_claim: string; actual_fact: string; distortion_type: string; severity: string }[];
      omissions?: { what_was_omitted: string; why_it_matters: string; severity: string }[];
    };
    session_id?: string;
    processing_time?: number;
  };
};

const manipLevel = (score: number) => {
  if (score <= 3) return { label: "LOW MANIPULATION", color: "text-score-high" };
  if (score <= 6) return { label: "MODERATE MANIPULATION", color: "text-score-moderate" };
  return { label: "HIGH MANIPULATION", color: "text-score-low" };
};

const sevColor = (s: string) => {
  switch (s?.toLowerCase()) {
    case "low": return "bg-score-high/15 text-score-high";
    case "moderate": return "bg-score-moderate/15 text-score-moderate";
    case "high": return "bg-score-low/15 text-score-low";
    default: return "bg-muted text-muted-foreground";
  }
};

const ManipulationReport = ({ data }: Props) => {
  const [showDetails, setShowDetails] = useState(false);
  const score = data.manipulation_score ?? 0;
  const level = manipLevel(score);
  const r = data.report;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-display font-semibold mb-1">Manipulation Check</h3>
        <p className="text-xs text-muted-foreground mb-4">
          We look for facts taken out of context, cherry-picked data, and misleading framing.
        </p>

        <div className="flex items-center gap-3 mb-3">
          <span className={cn("text-3xl font-bold font-display", level.color)}>
            {score.toFixed(1)}
          </span>
          <span className="text-sm text-muted-foreground">/10</span>
          <span className={cn("text-xs font-semibold uppercase", level.color)}>
            {level.label}
          </span>
        </div>

        {r?.narrative_summary && (
          <p className="text-sm leading-relaxed mb-4">{r.narrative_summary}</p>
        )}

        {r?.techniques_detected?.length ? (
          <div className="space-y-2 mb-3">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Techniques Detected
            </h4>
            {r.techniques_detected.map((t, i) => (
              <div key={i} className="rounded-lg border border-border p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium">{t.technique}</span>
                  <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase", sevColor(t.severity))}>
                    {t.severity}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{t.description}</p>
              </div>
            ))}
          </div>
        ) : null}

        {(r?.factual_distortions?.length || r?.omissions?.length) ? (
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View Detailed Analysis {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        ) : null}

        {showDetails && (
          <div className="mt-3 space-y-3">
            {r?.factual_distortions?.length ? (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Factual Distortions
                </h4>
                {r.factual_distortions.map((d, i) => (
                  <div key={i} className="rounded-lg bg-secondary p-3 mb-2 text-xs">
                    <p><strong>Claim:</strong> {d.original_claim}</p>
                    <p className="mt-1"><strong>Fact:</strong> {d.actual_fact}</p>
                  </div>
                ))}
              </div>
            ) : null}

            {r?.omissions?.length ? (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Key Omissions
                </h4>
                {r.omissions.map((o, i) => (
                  <div key={i} className="rounded-lg bg-secondary p-3 mb-2 text-xs">
                    <p><strong>Omitted:</strong> {o.what_was_omitted}</p>
                    <p className="mt-1"><strong>Why it matters:</strong> {o.why_it_matters}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        )}
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default ManipulationReport;
