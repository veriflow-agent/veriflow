// src/components/reports/BiasReport.tsx
import { useState } from "react";
import { cn } from "@/lib/utils";
import { SessionInfo } from "./shared";

type BiasModel = {
  bias_rating?: string;
  bias_score?: number;
  confidence?: string;
  summary?: string;
  bias_indicators?: { type: string; description: string; severity: string; examples?: string[] }[];
  language_analysis?: string;
  source_selection_analysis?: string;
  framing_analysis?: string;
};

type Props = {
  data: {
    analysis?: {
      gpt_analysis?: BiasModel;
      claude_analysis?: BiasModel;
      consensus?: {
        agreed_rating?: string;
        agreement_level?: string;
        combined_score?: number;
        summary?: string;
      };
    };
    session_id?: string;
    processing_time?: number;
  };
};

const tabs = ["GPT-4", "Claude", "Consensus"] as const;

const biasColor = (rating?: string) => {
  if (!rating) return "text-muted-foreground";
  const r = rating.toUpperCase();
  if (r.includes("LEFT")) return "text-blue-600";
  if (r.includes("RIGHT")) return "text-red-600";
  return "text-score-high";
};

const ModelView = ({ model }: { model?: BiasModel }) => {
  if (!model) return <p className="text-sm text-muted-foreground">No analysis available.</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className={cn("text-lg font-bold font-display", biasColor(model.bias_rating))}>
          {model.bias_rating || "N/A"}
        </span>
        {model.bias_score != null && (
          <span className="text-sm text-muted-foreground">{model.bias_score}/100</span>
        )}
      </div>
      {model.summary && <p className="text-sm leading-relaxed">{model.summary}</p>}

      {model.bias_indicators?.length ? (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Bias Indicators</h4>
          {model.bias_indicators.map((ind, i) => (
            <div key={i} className="rounded-lg bg-secondary p-3 text-sm">
              <span className="font-medium capitalize">{ind.type}</span>
              <span className="text-muted-foreground"> -- {ind.description}</span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const BiasReport = ({ data }: Props) => {
  const [tab, setTab] = useState<typeof tabs[number]>("Consensus");
  const a = data.analysis;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-lg font-display font-semibold mb-1">Bias Analysis</h3>
        <p className="text-xs text-muted-foreground mb-4">
          We detect political slant, loaded language, and one-sided framing.
        </p>

        <div className="flex gap-1 mb-4 rounded-lg bg-secondary p-1">
          {tabs.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                tab === t ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "GPT-4" && <ModelView model={a?.gpt_analysis} />}
        {tab === "Claude" && <ModelView model={a?.claude_analysis} />}
        {tab === "Consensus" && (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className={cn("text-lg font-bold font-display", biasColor(a?.consensus?.agreed_rating))}>
                {a?.consensus?.agreed_rating || "N/A"}
              </span>
              {a?.consensus?.combined_score != null && (
                <span className="text-sm text-muted-foreground">{a.consensus.combined_score}/100</span>
              )}
            </div>
            {a?.consensus?.summary && <p className="text-sm leading-relaxed">{a.consensus.summary}</p>}
          </div>
        )}
      </div>
      <SessionInfo sessionId={data.session_id} processingTime={data.processing_time} />
    </div>
  );
};

export default BiasReport;
