// src/components/reports/LLMOutputReport.tsx
import { cn } from "@/lib/utils";
import { SessionInfo } from "./shared";
import { ExternalLink } from "lucide-react";

type VerResult = {
  fact_text: string;
  source_url: string;
  source_domain: string;
  verification_score: number;
  verification_status: string;
  explanation: string;
};

type Props = {
  data: {
    results?: VerResult[];
    factCheck?: { results?: VerResult[] };
    session_id?: string;
    processing_time?: number;
    audit_url?: string;
  };
};

const statusStyles: Record<string, string> = {
  verified: "bg-score-high/15 text-score-high",
  partially_verified: "bg-score-moderate/15 text-score-moderate",
  unverified: "bg-score-low/15 text-score-low",
};

const LLMOutputReport = ({ data }: Props) => {
  const results = data.results || data.factCheck?.results || [];

  const verified = results.filter(r => r.verification_status === "verified").length;
  const issues = results.filter(r => r.verification_status === "partially_verified").length;
  const unverified = results.filter(r => r.verification_status === "unverified").length;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-display font-semibold mb-1">Verification Results</h3>

        <div className="flex gap-6 mb-4 p-3 rounded-lg bg-secondary">
          <div className="text-center">
            <span className="block text-lg font-bold text-score-high">{verified}</span>
            <span className="text-xs text-muted-foreground">Verified</span>
          </div>
          <div className="text-center">
            <span className="block text-lg font-bold text-score-moderate">{issues}</span>
            <span className="text-xs text-muted-foreground">Issues</span>
          </div>
          <div className="text-center">
            <span className="block text-lg font-bold text-score-low">{unverified}</span>
            <span className="text-xs text-muted-foreground">Unverified</span>
          </div>
        </div>

        <div className="space-y-3">
          {results.map((r, i) => {
            const score = Math.round(r.verification_score * 100);
            return (
              <div key={i} className="rounded-lg border border-border p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-muted-foreground">#{i + 1}</span>
                  <span className={cn(
                    "rounded px-2 py-0.5 text-[10px] font-semibold uppercase",
                    statusStyles[r.verification_status] || "bg-muted text-muted-foreground"
                  )}>
                    {r.verification_status?.replace("_", " ")}
                  </span>
                </div>
                <p className="text-sm font-medium mb-1">{r.fact_text}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{r.explanation}</p>
                {r.source_domain && (
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 mt-2 text-xs text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink size={10} /> {r.source_domain}
                  </a>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default LLMOutputReport;
