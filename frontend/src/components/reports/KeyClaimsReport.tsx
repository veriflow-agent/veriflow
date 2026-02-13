// src/components/reports/KeyClaimsReport.tsx
import { cn } from "@/lib/utils";
import { ScoreBadge, SessionInfo, getScoreColor } from "./shared";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

type Claim = {
  claim_id: number;
  claim_text: string;
  verification_status: string;
  verification_score: number;
  verification_summary: string;
  supporting_sources?: { url: string; title: string; domain: string; credibility_tier?: number }[];
  contradicting_sources?: { url: string; title: string; domain: string }[];
};

type Props = {
  data: {
    key_claims?: Claim[];
    no_claims_found?: boolean;
    summary?: { total_key_claims: number; verified_count: number; partial_count: number; unverified_count: number; overall_credibility: string };
    session_id?: string;
    processing_time?: number;
  };
};

const statusLabel = (s: string) => {
  switch (s) {
    case "verified": return "VERIFIED";
    case "partially_verified": return "PARTIALLY VERIFIED";
    case "unverified": return "UNVERIFIED";
    default: return s?.toUpperCase();
  }
};

const statusColor = (s: string) => {
  switch (s) {
    case "verified": return "text-score-high";
    case "partially_verified": return "text-score-moderate";
    case "unverified": return "text-score-low";
    default: return "text-muted-foreground";
  }
};

const KeyClaimsReport = ({ data }: Props) => {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (data.no_claims_found || !data.key_claims?.length) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <p className="text-sm text-muted-foreground">No verifiable claims found in this content.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-display font-semibold mb-1">Key Claims Analysis</h3>
        <p className="text-xs text-muted-foreground mb-4">
          We identify the 2-3 most important claims and verify each one thoroughly
        </p>

        {data.summary && (
          <div className="flex flex-wrap gap-4 mb-4 p-3 rounded-lg bg-secondary">
            <div className="text-center">
              <span className="block text-lg font-bold">{data.summary.total_key_claims}</span>
              <span className="text-xs text-muted-foreground">Claims</span>
            </div>
            <div className="text-center">
              <span className="block text-lg font-bold text-score-high">{data.summary.verified_count}</span>
              <span className="text-xs text-muted-foreground">Verified</span>
            </div>
            <div className="text-center">
              <span className="block text-lg font-bold text-score-moderate">{data.summary.partial_count}</span>
              <span className="text-xs text-muted-foreground">Partial</span>
            </div>
            <div className="text-center">
              <span className="block text-lg font-bold text-score-low">{data.summary.unverified_count}</span>
              <span className="text-xs text-muted-foreground">Unverified</span>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {data.key_claims.map((claim) => {
            const score = Math.round(claim.verification_score * 100);
            const isOpen = expanded[claim.claim_id];

            return (
              <div key={claim.claim_id} className="rounded-lg border border-border p-4">
                <div className="flex items-start gap-3">
                  <ScoreBadge score={score} className="shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-muted-foreground">
                        #{claim.claim_id} KEY CLAIM
                      </span>
                      <span className={cn("text-xs font-semibold", statusColor(claim.verification_status))}>
                        {statusLabel(claim.verification_status)}
                      </span>
                    </div>
                    <p className="text-sm font-medium mb-2">{claim.claim_text}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{claim.verification_summary}</p>

                    {(claim.supporting_sources?.length || claim.contradicting_sources?.length) && (
                      <button
                        onClick={() => setExpanded(prev => ({ ...prev, [claim.claim_id]: !isOpen }))}
                        className="flex items-center gap-1 mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Sources {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                    )}

                    {isOpen && claim.supporting_sources?.map((s, i) => (
                      <a
                        key={i}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 mt-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink size={10} /> {s.domain || s.title}
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default KeyClaimsReport;
