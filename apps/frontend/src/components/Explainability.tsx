import type { PatternSignal } from "../types";

export default function Explainability({
  signals,
  dataNotUsed,
}: {
  signals: PatternSignal[];
  dataNotUsed: string[];
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-slate-200 mb-2">Why this was detected</h3>
      {signals.length === 0 ? (
        <p className="text-sm text-slate-500">No sustained deviation from your baseline right now.</p>
      ) : (
        <ul className="space-y-1 text-sm text-slate-300">
          {signals.map((s) => (
            <li key={s.name}>
              {s.change >= 0 ? "+" : ""}
              {Math.round(s.change * 100)}% {s.name.replace(/_/g, " ")} over {s.anomalous_days} days
            </li>
          ))}
        </ul>
      )}
      <h4 className="text-xs font-semibold text-slate-500 mt-4 mb-1 uppercase tracking-wide">Data not used</h4>
      <p className="text-xs text-slate-500">{dataNotUsed.join(" · ")}</p>
    </div>
  );
}
