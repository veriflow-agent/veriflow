// src/components/reports/LLMOutputReport.tsx
import { cn } from "@/lib/utils";
import { SessionInfo } from "./shared";
import { ExternalLink, ChevronDown, ChevronUp, Lock, ShieldAlert } from "lucide-react";
import { useState } from "react";

// Backend LLMVerificationResult fields:
//   claim_id, claim_text, verification_score (0-1),
//   assessment, interpretation_issues, wording_comparison,
//   confidence, reasoning, excerpts, cited_source_urls
type VerResult = {
  claim_id: string;
  claim_text: string;           // was fact_text
  verification_score: number;
  assessment: string;           // was explanation
  interpretation_issues?: string[];
  wording_comparison?: Record<string, any>;
  confidence?: number;
  reasoning?: string;
  excerpts?: Record<string, any>[];
  cited_source_urls?: string[];  // was source_url / source_domain
  source_issues?: { url: string; domain: string; reason: string }[];
};

type Props = {
  data: {
    results?: VerResult[];
    factCheck?: { results?: VerResult[] };
    summary?: {
      average_score?: number;
      total_claims?: number;
      verified_count?: number;
      partial_count?: number;
      unverified_count?: number;
    };
    session_id?: string;
    processing_time?: number;
    duration?: number;          // backend uses duration, not processing_time
    audit_url?: string;
  };
};

// Derive status from verification_score
const deriveStatus = (score: number): string => {
  if (score >= 0.85) return "verified";
  if (score >= 0.6) return "partially_verified";
  return "unverified";
};

const statusStyles: Record<string, string> = {
  verified: "bg-score-high/15 text-score-high",
  partially_verified: "bg-score-moderate/15 text-score-moderate",
  unverified: "bg-score-low/15 text-score-low",
};

// Extract domain from URL for display
const getDomain = (url: string): string => {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
};

const LLMOutputReport = ({ data }: Props) => {
  const [expandedClaims, setExpandedClaims] = useState<Record<string, boolean>>({});
  const results = data.results || data.factCheck?.results || [];
  const processingTime = data.processing_time ?? data.duration;

  const verified = results.filter(r => deriveStatus(r.verification_score) === "verified").length;
  const issues = results.filter(r => deriveStatus(r.verification_score) === "partially_verified").length;
  const unverified = results.filter(r => deriveStatus(r.verification_score) === "unverified").length;

  // Collect unique source issues across all claims
  const allSourceIssues = new Map<string, { domain: string; reason: string }>();
  results.forEach(r => {
    r.source_issues?.forEach(si => {
      if (!allSourceIssues.has(si.url)) {
        allSourceIssues.set(si.url, { domain: si.domain, reason: si.reason });
      }
    });
  });
  const paywallCount = [...allSourceIssues.values()].filter(si => si.reason === "paywall").length;
  const blockedCount = [...allSourceIssues.values()].filter(si => si.reason !== "paywall").length;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-xl font-display font-semibold mb-1">Verification Results</h3>

        <div className="flex gap-6 mb-4 p-3 rounded-lg bg-secondary">
          <div className="text-center">
            <span className="block text-xl font-bold text-score-high">{verified}</span>
            <span className="text-sm text-muted-foreground">Verified</span>
          </div>
          <div className="text-center">
            <span className="block text-xl font-bold text-score-moderate">{issues}</span>
            <span className="text-sm text-muted-foreground">Issues</span>
          </div>
          <div className="text-center">
            <span className="block text-xl font-bold text-score-low">{unverified}</span>
            <span className="text-sm text-muted-foreground">Unverified</span>
          </div>
        </div>

        {/* Source access issues banner */}
        {allSourceIssues.size > 0 && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <Lock size={13} className="text-amber-500" />
              <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                Some sources could not be accessed
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {paywallCount > 0 && `${paywallCount} source${paywallCount > 1 ? "s" : ""} behind a paywall`}
              {paywallCount > 0 && blockedCount > 0 && ", "}
              {blockedCount > 0 && `${blockedCount} source${blockedCount > 1 ? "s" : ""} blocking automated access`}
              . Claims citing these sources could not be fully verified.
              Look for the links below to open them in your browser.
            </p>
          </div>
        )}

        <div className="space-y-3">
          {results.map((r, i) => {
            const score = Math.round(r.verification_score * 100);
            const status = deriveStatus(r.verification_score);
            const isExpanded = expandedClaims[r.claim_id || String(i)];

            return (
              <div key={r.claim_id || i} className="rounded-lg border border-border p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-semibold text-muted-foreground">#{i + 1}</span>
                  <span className={cn(
                    "rounded px-2 py-0.5 text-xs font-semibold uppercase",
                    statusStyles[status] || "bg-muted text-muted-foreground"
                  )}>
                    {status.replace("_", " ")}
                  </span>
                  <span className="text-sm text-muted-foreground ml-auto">{score}%</span>
                </div>
                <p className="text-base font-medium mb-1">{r.claim_text}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{r.assessment}</p>

                {/* Interpretation issues */}
                {r.interpretation_issues && r.interpretation_issues.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {r.interpretation_issues.map((issue, j) => (
                      <p key={j} className="text-sm text-score-low pl-3 border-l-2 border-score-low">
                        {issue}
                      </p>
                    ))}
                  </div>
                )}

                {/* Cited sources with failure status */}
                {r.cited_source_urls && r.cited_source_urls.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {r.cited_source_urls.map((url, j) => {
                      const issue = r.source_issues?.find(si => si.url === url);
                      if (issue) {
                        return (
                          <div key={j} className="flex items-start gap-2 mt-1 rounded border border-amber-500/30 bg-amber-500/5 px-2.5 py-1.5">
                            <div className="flex items-center gap-1 shrink-0 mt-px">
                              {issue.reason === "paywall" ? (
                                <Lock size={11} className="text-amber-500" />
                              ) : (
                                <ShieldAlert size={11} className="text-amber-500" />
                              )}
                              <span className="text-xs font-semibold uppercase text-amber-500">
                                {issue.reason === "paywall" ? "Paywall" : "Blocked"}
                              </span>
                            </div>
                            <div className="flex flex-col gap-0.5 min-w-0">
                              <span className="text-xs text-muted-foreground leading-tight">
                                {issue.reason === "paywall"
                                  ? "This article is behind a paywall. Open it in your browser to read the source:"
                                  : `${issue.domain} is blocking automated access. Open it in your browser:`}
                              </span>
                              <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-foreground hover:underline truncate"
                              >
                                <ExternalLink size={10} className="shrink-0" /> {getDomain(url)}
                              </a>
                            </div>
                          </div>
                        );
                      }
                      return (
                        <a
                          key={j}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 mt-1 text-sm text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink size={10} /> {getDomain(url)}
                        </a>
                      );
                    })}
                  </div>
                )}

                {/* Expandable reasoning */}
                {r.reasoning && (
                  <>
                    <button
                      onClick={() => setExpandedClaims(prev => ({
                        ...prev,
                        [r.claim_id || String(i)]: !isExpanded
                      }))}
                      className="flex items-center gap-1 mt-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Reasoning {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                    {isExpanded && (
                      <p className="mt-1 text-sm text-muted-foreground leading-relaxed pl-3 border-l-2 border-border">
                        {r.reasoning}
                      </p>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={processingTime} />
    </div>
  );
};

export default LLMOutputReport;