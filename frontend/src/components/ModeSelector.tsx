// src/components/ModeSelector.tsx
import { cn } from "@/lib/utils";
import type { AnalysisMode } from "@/lib/api";
import { MODE_INFO } from "@/lib/api";

const ALL_MODES: { id: AnalysisMode | "text-factcheck"; disabled?: boolean }[] = [
  { id: "comprehensive" },
  { id: "key-claims" },
  { id: "bias-analysis" },
  { id: "lie-detection" },
  { id: "manipulation" },
  { id: "llm-output" },
  { id: "text-factcheck", disabled: true },
];

type Props = {
  selected: AnalysisMode;
  onSelect: (mode: AnalysisMode) => void;
};

const ModeSelector = ({ selected, onSelect }: Props) => (
  <div>
    <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-3">
      Choose Analysis Mode
    </p>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {ALL_MODES.map((m) => {
        const isDisabled = m.disabled;
        const isSelected = selected === m.id;
        const info = (MODE_INFO as any)[m.id];

        return (
          <button
            key={m.id}
            disabled={isDisabled}
            onClick={() => !isDisabled && onSelect(m.id as AnalysisMode)}
            className={cn(
              "rounded-lg border px-4 py-3 text-left transition-all duration-200",
              isSelected
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card text-card-foreground border-border hover:border-foreground/30",
              isDisabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <span className="block text-sm font-semibold font-display">
              {info?.label || "Full Fact-Check"}
            </span>
            <span
              className={cn(
                "block text-xs mt-0.5",
                isSelected ? "text-primary-foreground/70" : "text-muted-foreground"
              )}
            >
              {isDisabled ? "Coming soon" : info?.description}
            </span>
          </button>
        );
      })}
    </div>
  </div>
);

export default ModeSelector;
