interface MetricBarProps {
  label: string;
  current: number;
  baseline: number;
  unit?: string;
}

export default function MetricBar({ label, current, baseline, unit = "" }: MetricBarProps) {
  const ratio = baseline > 0 ? current / baseline : current > 0 ? 1 : 0;

  // The baseline sits at the midpoint, so the scale runs 0 -> 2x your norm.
  // Filling the bar proportionally to the raw value instead would peg every
  // at-or-above-norm metric at 100% and show nothing, which is the whole
  // point of a chart whose subject is deviation rather than magnitude.
  const widthPct = Math.max(2, Math.min(100, ratio * 50));
  const deltaPct = baseline > 0 ? Math.round(((current - baseline) / baseline) * 100) : 0;
  const notable = Math.abs(deltaPct) >= 25;

  return (
    <div className="mb-5 last:mb-0">
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-slate-200 font-medium">{label}</span>
        <span className="text-slate-400">
          {current.toFixed(1)}
          {unit} ·{" "}
          <span className={notable ? "text-sky-300" : "text-slate-400"}>
            {deltaPct >= 0 ? "+" : ""}
            {deltaPct}% vs your norm
          </span>
        </span>
      </div>
      <div className="relative h-2.5 w-full bg-slate-800 rounded-full">
        <div
          className={`h-full rounded-full transition-all ${notable ? "bg-sky-400" : "bg-sky-600"}`}
          style={{ width: `${widthPct}%` }}
        />
        {/* Reference tick for "your norm" - without it the fill level is an
            arbitrary number rather than a comparison. */}
        <div
          className="absolute top-[-3px] h-[17px] w-px bg-slate-500"
          style={{ left: "50%" }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
