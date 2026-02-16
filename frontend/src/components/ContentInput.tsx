// src/components/ContentInput.tsx
import { useState, useEffect } from "react";
import { Link2 } from "lucide-react";

type Props = {
  content: string;
  onContentChange: (v: string) => void;
  url: string;
  onUrlChange: (v: string) => void;
  onFetchUrl: () => void;
  isFetching: boolean;
  mode: string;
};

const ContentInput = ({ content, onContentChange, url, onUrlChange, onFetchUrl, isFetching, mode }: Props) => {
  const [inputMode, setInputMode] = useState<"text" | "url">("text");

  // After a URL fetch completes and content is populated, switch to text view
  // so the user can see the fetched article text
  useEffect(() => {
    if (!isFetching && inputMode === "url" && content) {
      setInputMode("text");
    }
  }, [isFetching, content]);

  // LLM Output mode is copy-paste only — force text input and hide URL toggle
  const isLlmMode = mode === "llm-output";

  useEffect(() => {
    if (isLlmMode && inputMode === "url") {
      setInputMode("text");
    }
  }, [isLlmMode]);

  const placeholders: Record<string, string> = {
    "comprehensive": "Paste any article, text, or AI-generated content for full analysis...",
    "key-claims": "Paste text for Key Claims analysis...",
    "bias-analysis": "Paste text to analyze for bias...",
    "lie-detection": "Paste article or text to analyze...",
    "manipulation": "Paste article to check for manipulation...",
    "llm-output": "Paste LLM output with source links...",
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
    </div>
  );
};

export default ContentInput;