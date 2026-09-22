import { formatChange } from "../lib/formatSignal";
import type { PatternSignal } from "../types";

export default function Explainability({
  signals,
  dataNotUsed,
}: {
  signals: PatternSignal[];
  dataNotUsed: string[];
}) {
  return (
    <section className="panel p-5">
      <h2 className="eyebrow mb-3">Why this was detected</h2>

      {signals.length === 0 ? (
        <p className="text-[13px] text-text-muted">
          No sustained deviation from your baseline right now.
        </p>
      ) : (
        <ul className="space-y-2">
          {signals.map((s) => (
            <li key={s.name} className="flex items-center justify-between gap-4 text-[13.5px]">
              <span className="capitalize">{s.name.replace(/_/g, " ")}</span>
              <span className="font-mono text-[12px] tabular-nums text-accent shrink-0">
                {formatChange(s)}
                <span className="text-text-faint ml-2">{s.anomalous_days}d</span>
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 pt-4 border-t border-line-soft">
        <h3 className="eyebrow mb-1.5">Data not used</h3>
        <p className="text-[12px] text-text-faint">{dataNotUsed.join(" · ")}</p>
      </div>
    </section>
  );
}
