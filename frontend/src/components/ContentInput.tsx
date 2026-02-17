// src/components/ContentInput.tsx
import { useState, useEffect, useMemo } from "react";
import { Link2, CheckCircle2, AlertTriangle } from "lucide-react";

type Props = {
  content: string;
  onContentChange: (v: string) => void;
  url: string;
  onUrlChange: (v: string) => void;
  onFetchUrl: () => void;
  isFetching: boolean;
  mode: string;
  onSwitchMode?: (mode: string) => void;
};

// ---------------------------------------------------------------------------
// Link detection helpers (mirrors the old vanilla-JS utils)
// ---------------------------------------------------------------------------

function countLinks(text: string): number {
  if (!text) return 0;

  let count = 0;

  // HTML anchor tags
  const htmlMatches = text.match(/<\s*a\s+[^>]*href\s*=\s*["'][^"']+["'][^>]*>/gi);
  if (htmlMatches) count += htmlMatches.length;

  // Markdown reference links  [1]: https://...
  const refMatches = text.match(/^\s*\[\d+\]\s*:\s*https?:\/\//gm);
  if (refMatches) count += refMatches.length;

  // Markdown inline links  [text](https://...)
  const inlineMatches = text.match(/\[[^\]]+\]\(https?:\/\/[^)]+\)/g);
  if (inlineMatches) count += inlineMatches.length;

  // Fall back to plain URLs only if no structured links found
  if (count === 0) {
    const urlMatches = text.match(/https?:\/\/[^\s<>"']+/g);
    if (urlMatches) count = urlMatches.length;
  }

  return count;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ContentInput = ({
  content, onContentChange, url, onUrlChange,
  onFetchUrl, isFetching, mode, onSwitchMode,
}: Props) => {
  const [inputMode, setInputMode] = useState<"text" | "url">("text");

  // After a URL fetch completes and content is populated, switch to text view
  // so the user can see the fetched article text
  useEffect(() => {
    if (!isFetching && inputMode === "url" && content) {
      setInputMode("text");
    }
  }, [isFetching, content]);

  // LLM Output mode is copy-paste only -- force text input and hide URL toggle
  const isLlmMode = mode === "llm-output";

  useEffect(() => {
    if (isLlmMode && inputMode === "url") {
      setInputMode("text");
    }
  }, [isLlmMode]);

  // --- Link detection (only evaluated in LLM Output mode) ----------------
  const linkCount = useMemo(
    () => (isLlmMode ? countLinks(content) : 0),
    [content, isLlmMode],
  );

  // Only show indicator once the user has typed enough (avoids flashing)
  const showIndicator = isLlmMode && content.length > 50;
  const hasLinks = linkCount > 0;

  const placeholders: Record<string, string> = {
    "comprehensive": "Runs all applicable analyses in one pass – source credibility, claims verification, bias, deception, and manipulation. Paste any article, text, or AI-generated content...",
    "key-claims": "Identifies the 2-3 strongest factual claims and verifies each against independent sources. Paste the article or text you want to check...",
    "bias-analysis": "Detects political or ideological lean, framing techniques, and one-sided sourcing patterns. Paste a news article, op-ed, or any content...",
    "lie-detection": "Scans for linguistic markers of deception, hedging, and unsupported assertions. Paste the article or text to analyze...",
    "manipulation": "Flags agenda-driven framing, cherry-picked data, false equivalences, and emotional manipulation techniques. Paste an article or text to check...",
    "llm-output": "Checks whether AI-generated text matches the sources it cites - flags unsupported claims, missing context, and citation errors. Paste output with source links from ChatGPT, Perplexity, etc...",
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold">
          {inputMode === "text" ? "Content to Analyze" : "Article URL"}
        </h3>
        {!isLlmMode && (
          <button
            onClick={() => setInputMode(inputMode === "text" ? "url" : "text")}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <Link2 size={14} />
            {inputMode === "text" ? "Paste URL instead" : "Paste text instead"}
          </button>
        )}
      </div>

      {inputMode === "text" ? (
        <textarea
          value={content}
          onChange={(e) => onContentChange(e.target.value)}
          placeholder={placeholders[mode] || placeholders.comprehensive}
          className="w-full min-h-[200px] resize-y rounded-lg border border-border bg-background p-3 text-base placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
      ) : (
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://example.com/article"
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-base placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button
            onClick={onFetchUrl}
            disabled={isFetching || !url}
            className="rounded-lg bg-primary px-4 py-2 text-base font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isFetching ? "Fetching..." : "Fetch"}
          </button>
        </div>
      )}

      {/* --- Link format indicator (LLM Output mode only) --- */}
      {showIndicator && (
        <div
          className={`flex items-start gap-2.5 mt-3 px-3.5 py-2.5 rounded-lg text-sm ${
            hasLinks
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
              : "bg-amber-500/10 text-amber-700 dark:text-amber-400"
          }`}
        >
          {hasLinks ? (
            <>
              <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
              <span>
                Detected {linkCount} source link{linkCount !== 1 ? "s" : ""}
              </span>
            </>
          ) : (
            <>
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <span>
                No source links detected. LLM Output mode verifies AI responses against their
                cited sources.{" "}
                {onSwitchMode && (
                  <>
                    Try{" "}
                    <button
                      type="button"
                      onClick={() => onSwitchMode("comprehensive")}
                      className="underline font-medium hover:opacity-80"
                    >
                      Comprehensive Analysis
                    </button>{" "}
                    or{" "}
                    <button
                      type="button"
                      onClick={() => onSwitchMode("key-claims")}
                      className="underline font-medium hover:opacity-80"
                    >
                      Key Claims
                    </button>{" "}
                    for text without links.
                  </>
                )}
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ContentInput;