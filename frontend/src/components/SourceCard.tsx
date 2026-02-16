// src/components/SourceCard.tsx
import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  article: {
    title?: string;
    author?: string;
    publication_name?: string;
    publication_date?: string;
    url?: string;
    domain?: string;
    content_length?: number;
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
};

const tierLabels: Record<number, string> = {
  1: "Highly Credible",
  2: "Credible",
  3: "Mixed Credibility",
  4: "Low Credibility",
  5: "Unreliable",
};

const tierColors: Record<number, string> = {
  1: "bg-score-high text-accent-foreground",
  2: "bg-tier-2 text-accent-foreground",
  3: "bg-score-moderate text-foreground",
  4: "bg-score-elevated text-accent-foreground",
  5: "bg-score-low text-accent-foreground",
};

const SourceCard = ({ article }: Props) => {
  const [showDetails, setShowDetails] = useState(false);
  const cred = article.credibility;
  const tier = cred?.tier || 0;

  // Check if there are any MBFC details worth showing in the dropdown
  const hasDetails =
    cred?.bias_rating ||
    cred?.factual_reporting ||
    cred?.rating ||
    cred?.reasoning ||
    cred?.mbfc_url ||
    cred?.is_propaganda ||
    (cred?.special_tags && cred.special_tags.length > 0);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h4 className="text-base font-semibold mb-1 font-display">Source Article</h4>

      {article.title && (
        <p className="text-base font-medium leading-snug mb-1">{article.title}</p>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
        {article.author && <span>{article.author}</span>}
        {article.publication_date && <span>{article.publication_date}</span>}
        {article.publication_name && <span>{article.publication_name}</span>}
      </div>

      {tier > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <span className={cn("rounded px-2 py-0.5 text-sm font-medium", tierColors[tier])}>
            Tier {tier}
          </span>
          <span className="text-sm text-muted-foreground">
            {tierLabels[tier]}
          </span>

          {/* Expand/collapse toggle -- only if there are details to show */}
          {hasDetails && (
            <button
              onClick={() => setShowDetails((v) => !v)}
              className="ml-auto flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>{showDetails ? "Hide details" : "Show details"}</span>
              {showDetails
                ? <ChevronUp size={12} />
                : <ChevronDown size={12} />
              }
            </button>
          )}
        </div>
      )}

      {/* Expandable credibility details */}
      {showDetails && hasDetails && (
        <div className="mt-3 rounded-lg border border-border bg-background p-3">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-border">
              {cred?.bias_rating && (
                <tr>
                  <td className="py-1.5 pr-4 text-muted-foreground whitespace-nowrap">Bias Rating</td>
                  <td className="py-1.5 font-medium">{cred.bias_rating}</td>
                </tr>
              )}
              {cred?.factual_reporting && (
                <tr>
                  <td className="py-1.5 pr-4 text-muted-foreground whitespace-nowrap">Factual Reporting</td>
                  <td className="py-1.5 font-medium">{cred.factual_reporting}</td>
                </tr>
              )}
              {cred?.rating && (
                <tr>
                  <td className="py-1.5 pr-4 text-muted-foreground whitespace-nowrap">Credibility Rating</td>
                  <td className="py-1.5 font-medium">{cred.rating}</td>
                </tr>
              )}
              {cred?.source && (
                <tr>
                  <td className="py-1.5 pr-4 text-muted-foreground whitespace-nowrap">Data Source</td>
                  <td className="py-1.5 font-medium capitalize">{cred.source}</td>
                </tr>
              )}
              {cred?.reasoning && (
                <tr>
                  <td className="py-1.5 pr-4 text-muted-foreground whitespace-nowrap">Reasoning</td>
                  <td className="py-1.5 text-muted-foreground">{cred.reasoning}</td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Propaganda warning */}
          {cred?.is_propaganda && (
            <div className="mt-2 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
              Identified as propaganda source
            </div>
          )}

          {/* Special tags */}
          {cred?.special_tags && cred.special_tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {cred.special_tags.map((tag, i) => (
                <span key={i} className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* MBFC link */}
          {cred?.mbfc_url && (
            <a
              href={cred.mbfc_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              View MBFC Report
              <ExternalLink size={10} />
            </a>
          )}
        </div>
      )}

      {article.content_length && (
        <p className="text-sm text-muted-foreground mt-1">
          {(article.content_length / 1000).toFixed(1)}k characters extracted
        </p>
      )}
    </div>
  );
};

export default SourceCard;
