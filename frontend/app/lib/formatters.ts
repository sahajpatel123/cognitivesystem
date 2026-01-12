import { ExecutionRun, OPERATIONAL_PATTERNS, PipelineState } from "./static-data";

export function formatSecondsAsClock(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function formatPipelineState(state: PipelineState): string {
  return state.charAt(0).toUpperCase() + state.slice(1);
}

export function formatRiskClassification(
  risk: ExecutionRun["riskClassification"],
): string {
  switch (risk) {
    case "low":
      return "Risk classification: Low";
    case "elevated":
      return "Risk classification: Elevated";
    case "out_of_scope":
      return "Risk classification: Out-of-scope";
    default:
      return "Risk classification: Unknown";
  }
}

export function operationalPatternLabel(id: string): string {
  return OPERATIONAL_PATTERNS.find((pattern) => pattern.id === id)?.label ?? id;
}
