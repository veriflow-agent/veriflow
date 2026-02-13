// src/components/reports/shared.tsx
import { cn } from "@/lib/utils";

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-score-high";
  if (score >= 60) return "text-score-moderate";
  if (score >= 40) return "text-score-elevated";
  return "text-score-low";
}

export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-score-high";
  if (score >= 60) return "bg-score-moderate";
  if (score >= 40) return "bg-score-elevated";
  return "bg-score-low";
}

export function getScoreLabel(score: number): string {
  if (score >= 80) return "Highly Credible";
  if (score >= 60) return "Credible";
  if (score >= 40) return "Mixed";
  return "Low Credibility";
}

export function getRiskColor(level: string): string {
  switch (level?.toLowerCase()) {
    case "low": return "text-score-high";
    case "moderate": return "text-score-moderate";
    case "high": return "text-score-low";
    default: return "text-muted-foreground";
  }
}

export function getRiskBg(level: string): string {
  switch (level?.toLowerCase()) {
    case "low": return "bg-score-high";
    case "moderate": return "bg-score-moderate";
    case "high": return "bg-score-low";
    default: return "bg-muted";
  }
}

type ScoreBadgeProps = { score: number; label?: string; className?: string };

export const ScoreBadge = ({ score, label, className }: ScoreBadgeProps) => (
  <div className={cn("flex flex-col items-center", className)}>
    <span className={cn("text-3xl font-bold font-display", getScoreColor(score))}>
      {Math.round(score)}
    </span>
    {label && <span className="text-xs text-muted-foreground mt-0.5">{label}</span>}
  </div>
);

type RiskBadgeProps = { level: string; className?: string };

export const RiskBadge = ({ level, className }: RiskBadgeProps) => (
  <span className={cn("rounded-full px-3 py-1 text-xs font-semibold uppercase text-accent-foreground", getRiskBg(level), className)}>
    {level} Risk
  </span>
);

type SessionInfoProps = { sessionId?: string; processingTime?: number };

export const SessionInfo = ({ sessionId, processingTime }: SessionInfoProps) => (
  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-4 pt-3 border-t border-border">
    {sessionId && <span>Session ID: {sessionId}</span>}
    {processingTime != null && <span>Processing Time: {Math.round(processingTime)}s</span>}
  </div>
);
