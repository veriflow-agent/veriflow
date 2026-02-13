// src/components/SourceCard.tsx
import { cn } from "@/lib/utils";

type Props = {
  article: {
    title?: string;
    author?: string;
    publication_name?: string;
    publication_date?: string;
    content_length?: number;
    credibility?: {
      tier?: number;
      rating?: string;
      bias_rating?: string;
      factual_reporting?: string;
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
  const cred = article.credibility;
  const tier = cred?.tier || 0;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h4 className="text-sm font-semibold mb-1 font-display">Source Article</h4>

      {article.title && (
        <p className="text-sm font-medium leading-snug mb-1">{article.title}</p>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {article.author && <span>{article.author}</span>}
        {article.publication_date && <span>{article.publication_date}</span>}
        {article.publication_name && <span>{article.publication_name}</span>}
      </div>

      {tier > 0 && (
        <div className="mt-2 flex items-center gap-2">
          <span className={cn("rounded px-2 py-0.5 text-xs font-medium", tierColors[tier])}>
            Tier {tier}
          </span>
          <span className="text-xs text-muted-foreground">
            {tierLabels[tier]}
          </span>
        </div>
      )}

      {article.content_length && (
        <p className="text-xs text-muted-foreground mt-1">
          {(article.content_length / 1000).toFixed(1)}k characters extracted
        </p>
      )}
    </div>
  );
};

export default SourceCard;
