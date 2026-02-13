// src/components/reports/KeyClaimsReport.tsx
import { cn } from "@/lib/utils";
import { ScoreBadge, SessionInfo, getScoreColor } from "./shared";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

// Backend FactCheckResult fields:
//   fact_id (str), statement (str), match_score (float 0-1),
//   confidence (float 0-1), report (str), tier_breakdown (dict)
type Claim = {
  id: string;
  statement: string;        // was claim_text
  match_score: number;      // was verification_score (0-1 range)
  confidence: number;
  report: string;           // was verification_summary
  tier_breakdown?: { tier1?: number; tier2?: number; tier3?: number; filtered?: number } | null;
};

type Props = {
  data: {
    facts?: Claim[];         // was key_claims
    no_claims_found?: boolean;
    summary?: {
      total_facts: number;   // was total_key_claims
      average_score?: number;
      verified_count: number;
      partial_count: number;
      unverified_count: number;
    };
    session_id?: string;
    processing_time?: number;
  };
};

// Derive verification status from match_score
const deriveStatus = (score: number): string => {
  if (score >= 0.9) return "verified";
  if (score >= 0.7) return "partially_verified";
  return "unverified";
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
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Backend returns "facts", not "key_claims"
  const claims = data.facts;

  if (data.no_claims_found || !claims?.length) {
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
              <span className="block text-lg font-bold">{data.summary.total_facts}</span>
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
          {claims.map((claim) => {
            const scorePercent = Math.round(claim.match_score * 100);
            const status = deriveStatus(claim.match_score);
            const isOpen = expanded[claim.id];

            return (
              <div key={claim.id} className="rounded-lg border border-border p-4">
                <div className="flex items-start gap-3">
                  <ScoreBadge score={scorePercent} className="shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-muted-foreground">
                        #{claim.id} KEY CLAIM
                      </span>
                      <span className={cn("text-xs font-semibold", statusColor(status))}>
                        {statusLabel(status)}
                      </span>
                    </div>
                    <p className="text-sm font-medium mb-2">{claim.statement}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{claim.report}</p>

                    {claim.tier_breakdown && (
                      <button
                        onClick={() => setExpanded(prev => ({ ...prev, [claim.id]: !isOpen }))}
                        className="flex items-center gap-1 mt-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Source Tiers {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                    )}

                    {isOpen && claim.tier_breakdown && (
                      <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
                        {claim.tier_breakdown.tier1 != null && claim.tier_breakdown.tier1 > 0 && (
                          <span>Tier 1: {claim.tier_breakdown.tier1}</span>
                        )}
                        {claim.tier_breakdown.tier2 != null && claim.tier_breakdown.tier2 > 0 && (
                          <span>Tier 2: {claim.tier_breakdown.tier2}</span>
                        )}
                        {claim.tier_breakdown.tier3 != null && claim.tier_breakdown.tier3 > 0 && (
                          <span>Tier 3: {claim.tier_breakdown.tier3}</span>
                        )}
                      </div>
                    )}
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
