import Sparkline from "./Sparkline";

interface MetricBarProps {
  label: string;
  current: number;
  baseline: number;
  unit?: string;
  history?: number[];
}

export default function MetricBar({ label, current, baseline, unit = "", history }: MetricBarProps) {
  const ratio = baseline > 0 ? current / baseline : current > 0 ? 1 : 0;

  // The baseline sits at the midpoint, so the scale runs 0 -> 2x your norm.
  // Filling proportionally to the raw value instead would peg every
  // at-or-above-norm metric at 100% and show nothing, which is the whole
  // point of a chart whose subject is deviation rather than magnitude.
  const widthPct = Math.max(2, Math.min(100, ratio * 50));
  const deltaPct = baseline > 0 ? Math.round(((current - baseline) / baseline) * 100) : 0;
  const notable = Math.abs(deltaPct) >= 25;

  return (
    <div className="py-4 border-b border-line-soft last:border-0 first:pt-0 last:pb-0">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <span className="text-[13.5px] font-medium">{label}</span>
        <div className="flex items-center gap-3 shrink-0">
          {history && history.length > 1 && (
            <Sparkline values={history} className="opacity-80 hidden sm:block" />
          )}
          <span className="font-mono text-[12px] tabular-nums text-text-muted">
            {current.toFixed(1)}
            {unit}
            <span className={notable ? "text-accent ml-1.5" : "ml-1.5"}>
              {deltaPct >= 0 ? "+" : ""}
              {deltaPct}%
            </span>
          </span>
        </div>
      </div>

      <div className="relative h-2 rounded-full bg-surface-sunken border border-line-soft">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            notable ? "bg-accent" : "bg-accent-deep"
          }`}
          style={{ width: `${widthPct}%` }}
        />
        {/* Reference tick for "your norm" - without it the fill level is an
            arbitrary number rather than a comparison. */}
        <div className="absolute left-1/2 -top-1 -bottom-1 w-px bg-[#44566f]" aria-hidden="true" />
      </div>
    </div>
  );
}
