// src/components/SourceCard.tsx
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

export type ArticleData = {
  url?: string;
  domain?: string;
  title?: string;
  author?: string;
  publication_name?: string;
  publication_date?: string;
  publication_date_raw?: string;
  article_type?: string;
  section?: string;
  content_length?: number;
  metadata_confidence?: number;
  scrape_failed?: boolean;
  scrape_error?: string;
  scrape_error_type?: string;
  credibility?: {
    tier?: number;
    tier_description?: string;
    rating?: string;
    bias_rating?: string;
    factual_reporting?: string;
    is_propaganda?: boolean;
    special_tags?: string[];
    source?: string;
    reasoning?: string;
    mbfc_url?: string;
  };
};

type Props = {
  article: ArticleData;
};

const tierLabels: Record<number, string> = {
  1: "Highly Credible",
  2: "Credible",
  3: "Mixed Credibility",
  4: "Low Credibility",
  5: "Unreliable",
};

const tierColors: Record<number, string> = {
  1: "bg-tier-1 text-white",
  2: "bg-tier-2 text-white",
  3: "bg-tier-3 text-foreground",
  4: "bg-tier-4 text-white",
  5: "bg-tier-5 text-white",
};

const biasColors: Record<string, string> = {
  "LEFT": "text-blue-700",
  "LEFT-CENTER": "text-blue-600",
  "LEAST BIASED": "text-emerald-700",
  "RIGHT-CENTER": "text-red-500",
  "RIGHT": "text-red-700",
  "PRO-SCIENCE": "text-emerald-600",
};

const factualColors: Record<string, string> = {
  "VERY HIGH": "text-emerald-700",
  "HIGH": "text-emerald-600",
  "MOSTLY FACTUAL": "text-lime-700",
  "MIXED": "text-amber-600",
  "LOW": "text-orange-600",
  "VERY LOW": "text-red-600",
};

function getBiasColor(bias: string): string {
  const key = bias.toUpperCase();
  return biasColors[key] || "text-muted-foreground";
}

function getFactualColor(factual: string): string {
  const key = factual.toUpperCase();
  return factualColors[key] || "text-muted-foreground";
}

const SourceCard = ({ article }: Props) => {
  const [expanded, setExpanded] = useState(false);
  const cred = article.credibility;
  const tier = cred?.tier || 0;
  const hasCred = cred && cred.source !== "unknown";
  const hasMetadata = article.title || article.author || article.publication_date;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              Source Article
            </h4>

            {/* Title */}
            {article.title && (
              <p className="text-sm font-semibold leading-snug mb-1.5 line-clamp-2">
                {article.title}
              </p>
            )}

            {/* Author / Date / Publication / Type */}
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
              {article.publication_name && (
                <span className="font-medium text-foreground/70">
                  {article.publication_name}
                </span>
              )}
              {article.author && (
                <>
                  {article.publication_name && <span aria-hidden>|</span>}
                  <span>{article.author}</span>
                </>
              )}
              {(article.publication_date || article.publication_date_raw) && (
                <>
                  {(article.publication_name || article.author) && <span aria-hidden>|</span>}
                  <span>{article.publication_date || article.publication_date_raw}</span>
                </>
              )}
              {article.article_type && (
                <>
                  <span aria-hidden>|</span>
                  <span className="capitalize">{article.article_type}</span>
                </>
              )}
              {article.section && (
                <>
                  <span aria-hidden>|</span>
                  <span className="capitalize">{article.section}</span>
                </>
              )}
            </div>
          </div>

          {/* URL link */}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              title="Open source"
            >
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </div>

      {/* Scrape failure banner */}
      {article.scrape_failed && (
        <div className="mx-4 mb-3 rounded-lg bg-destructive/8 border border-destructive/20 px-3 py-2">
          <p className="text-xs font-medium text-destructive">
            Content extraction failed
            {article.scrape_error_type === "paywall" && " -- paywall detected"}
            {article.scrape_error_type === "blocked" && " -- site blocked access"}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Paste the article text manually to continue analysis.
          </p>
        </div>
      )}

      {/* Credibility row - always visible if we have tier data */}
      {tier > 0 && (
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5 flex-wrap">
              {/* Tier badge */}
              <span
                className={cn(
                  "rounded px-2 py-0.5 text-xs font-semibold",
                  tierColors[tier] || "bg-muted text-muted-foreground"
                )}
              >
                Tier {tier}
              </span>
              <span className="text-xs text-muted-foreground">
                {tierLabels[tier]}
              </span>

              {/* Bias rating */}
              {cred?.bias_rating && (
                <span className={cn("text-xs font-medium", getBiasColor(cred.bias_rating))}>
                  {cred.bias_rating}
                </span>
              )}
            </div>

            {/* Expand toggle if there's more to show */}
            {hasCred && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {expanded ? "Less" : "Details"}
                {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          {/* Propaganda warning - always visible */}
          {cred?.is_propaganda && (
            <div className="mt-2 rounded bg-destructive/10 border border-destructive/20 px-2.5 py-1.5">
              <span className="text-xs font-semibold text-destructive">
                WARNING: Identified as propaganda source
              </span>
            </div>
          )}

          {/* Special tags - always visible */}
          {cred?.special_tags && cred.special_tags.length > 0 && !cred.is_propaganda && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {cred.special_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Expanded details */}
          {expanded && hasCred && (
            <div className="mt-3 pt-3 border-t border-border/60 space-y-2">
              {/* Detail grid */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                {cred?.factual_reporting && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wide text-muted-foreground block">
                      Factual Reporting
                    </span>
                    <span className={cn("text-xs font-medium", getFactualColor(cred.factual_reporting))}>
                      {cred.factual_reporting}
                    </span>
                  </div>
                )}

                {cred?.rating && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wide text-muted-foreground block">
                      Credibility Rating
                    </span>
                    <span className="text-xs font-medium">{cred.rating}</span>
                  </div>
                )}

                {cred?.bias_rating && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wide text-muted-foreground block">
                      Bias Rating
                    </span>
                    <span className={cn("text-xs font-medium", getBiasColor(cred.bias_rating))}>
                      {cred.bias_rating}
                    </span>
                  </div>
                )}

                {cred?.source && (
                  <div>
                    <span className="text-[11px] uppercase tracking-wide text-muted-foreground block">
                      Data Source
                    </span>
                    <span className="text-xs font-medium capitalize">{cred.source}</span>
                  </div>
                )}
              </div>

              {/* Special tags in expanded view */}
              {cred?.special_tags && cred.special_tags.length > 0 && cred.is_propaganda && (
                <div className="flex flex-wrap gap-1.5">
                  {cred.special_tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Tier reasoning */}
              {cred?.reasoning && (
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {cred.reasoning}
                </p>
              )}

              {/* MBFC link */}
              {cred?.mbfc_url && (
                <a
                  href={cred.mbfc_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
                >
                  View MBFC Report
                  <ExternalLink size={10} />
                </a>
              )}
            </div>
          )}
        </div>
      )}

      {/* Content stats footer */}
      {article.content_length && !article.scrape_failed && (
        <div className="border-t border-border/60 px-4 py-2">
          <span className="text-[11px] text-muted-foreground">
            {(article.content_length / 1000).toFixed(1)}k characters extracted
          </span>
        </div>
      )}
    </div>
  );
};

export default SourceCard;
