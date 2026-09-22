import type { PatternSignal } from "../types";

/** Signals centred near zero (recovery_gap, typing_deviation) can't be read
 *  as a percentage of their own centre, so each carries the unit it is in.
 *  Kept in one place so the dashboard and the timeline never disagree. */
export function formatChange(signal: PatternSignal): string {
  const sign = signal.change >= 0 ? "+" : "−";
  const magnitude = Math.abs(signal.change);

  if (signal.change_kind === "spread") {
    return `${sign}${magnitude.toFixed(1)}× usual variation`;
  }
  if (signal.change_kind === "absolute") {
    return `${sign}${magnitude.toFixed(2)}`;
  }
  return `${sign}${Math.round(magnitude * 100)}%`;
}

export function signalLabel(name: string): string {
  return name.replace(/_/g, " ");
}
