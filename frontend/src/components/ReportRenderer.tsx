// src/components/ReportRenderer.tsx
import type { AnalysisMode } from "@/lib/api";
import ComprehensiveReport from "./reports/ComprehensiveReport";
import KeyClaimsReport from "./reports/KeyClaimsReport";
import BiasReport from "./reports/BiasReport";
import DeceptionReport from "./reports/DeceptionReport";
import ManipulationReport from "./reports/ManipulationReport";
import LLMOutputReport from "./reports/LLMOutputReport";

type Props = {
  mode: AnalysisMode;
  data: any;
  onReset: () => void;
};

const ReportRenderer = ({ mode, data, onReset }: Props) => {
  const renderReport = () => {
    switch (mode) {
      case "comprehensive": return <ComprehensiveReport data={data} />;
      case "key-claims": return <KeyClaimsReport data={data} />;
      case "bias-analysis": return <BiasReport data={data} />;
      case "lie-detection": return <DeceptionReport data={data} />;
      case "manipulation": return <ManipulationReport data={data} />;
      case "llm-output": return <LLMOutputReport data={data} />;
      default: return <pre className="text-xs overflow-auto">{JSON.stringify(data, null, 2)}</pre>;
    }
  };

  return (
    <div className="space-y-4">
      {renderReport()}
      <div className="flex justify-center gap-3 pt-2">
        <button
          onClick={onReset}
          className="rounded-lg border border-border px-5 py-2 text-sm font-medium hover:bg-secondary transition-colors"
        >
          Analyze Another
        </button>
      </div>
    </div>
  );
};

export default ReportRenderer;
