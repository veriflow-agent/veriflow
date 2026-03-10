// src/components/ModeSelector.tsx
import { cn } from "@/lib/utils";
import type { AnalysisMode } from "@/lib/api";
import { MODE_INFO } from "@/lib/api";

const ALL_MODES: { id: AnalysisMode | "text-factcheck"; disabled?: boolean }[] = [
  { id: "llm-output" },
  { id: "comprehensive" },
  { id: "key-claims" },
  { id: "bias-analysis" },
  { id: "lie-detection" },
  { id: "manipulation" },
  { id: "text-factcheck", disabled: true },
];

type Props = {
  selected: AnalysisMode;
  onSelect: (mode: AnalysisMode) => void;
  analyzedMode?: AnalysisMode | null;
};

const ModeSelector = ({ selected, onSelect, analyzedMode }: Props) => (
  <nav className="flex flex-col gap-1">
    <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      Analysis Mode
    </p>
    {ALL_MODES.map((m) => {
      const isDisabled = m.disabled;
      const isSelected = selected === m.id;
      const isAnalyzed = analyzedMode === m.id;
      const info = (MODE_INFO as any)[m.id];

      return (
        <button
          key={m.id}
          disabled={isDisabled}
          onClick={() => !isDisabled && onSelect(m.id as AnalysisMode)}
          className={cn(
            "w-full rounded-md px-3 py-2.5 text-left text-sm transition-colors",
            isSelected
              ? "bg-primary text-primary-foreground"
              : "text-foreground/80 hover:bg-accent",
            isDisabled && "opacity-40 cursor-not-allowed",
            !isSelected && isAnalyzed && "ring-1 ring-primary/30"
          )}
        >
          <span className="block font-medium leading-tight">
            {info?.label || "Full Fact-Check"}
          </span>
          {isDisabled && (
            <span className="block text-xs opacity-60 mt-0.5">Coming soon</span>
          )}
        </button>
      );
    })}
  </nav>
);

export default ModeSelector;
