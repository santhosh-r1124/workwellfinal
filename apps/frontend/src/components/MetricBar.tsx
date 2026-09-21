interface MetricBarProps {
  label: string;
  current: number;
  baseline: number;
  unit?: string;
}

export default function MetricBar({ label, current, baseline, unit = "" }: MetricBarProps) {
  const ratio = baseline > 0 ? current / baseline : current > 0 ? 1 : 0;
  const widthPct = Math.max(4, Math.min(100, ratio * 100));
  const deltaPct = baseline > 0 ? Math.round(((current - baseline) / baseline) * 100) : 0;

  return (
    <div className="mb-4 last:mb-0">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-200 font-medium">{label}</span>
        <span className="text-slate-400">
          {current.toFixed(1)}
          {unit} · {deltaPct >= 0 ? "+" : ""}
          {deltaPct}% vs your norm
        </span>
      </div>
      <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full bg-sky-500 rounded-full transition-all" style={{ width: `${widthPct}%` }} />
      </div>
    </div>
  );
}
