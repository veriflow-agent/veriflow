// src/components/ProgressLog.tsx
import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

type Props = {
  messages: string[];
  isActive: boolean;
  onCancel: () => void;
};

const ProgressLog = ({ messages, isActive, onCancel }: Props) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isActive && <Loader2 size={16} className="animate-spin text-muted-foreground" />}
          <h3 className="text-sm font-semibold">
            {isActive ? "Analyzing content..." : "Analysis complete"}
          </h3>
        </div>
        {isActive && (
          <button
            onClick={onCancel}
            className="rounded-lg border border-border px-3 py-1 text-xs font-medium hover:bg-secondary transition-colors"
          >
            Stop
          </button>
        )}
      </div>

      <div className="max-h-[200px] overflow-y-auto space-y-1 text-xs text-muted-foreground font-mono">
        {messages.map((msg, i) => (
          <p key={i} className={i === messages.length - 1 && isActive ? "animate-pulse-subtle" : ""}>
            {msg}
          </p>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default ProgressLog;
