import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { SelfReportPoint } from "../types";
import Sparkline from "./Sparkline";

const LINES: { key: "stress" | "energy" | "recovery"; label: string }[] = [
  { key: "stress", label: "Stress" },
  { key: "energy", label: "Energy" },
  { key: "recovery", label: "Recovery" },
];

/** The wellbeing pulse: the trend of the employee's own 1-5 check-ins over
 *  time. Deliberately the person's own ratings, not a measured signal - the
 *  one line on the dashboard that is ground truth rather than proxy. It
 *  reuses the same Sparkline as the measured metrics so the two read as the
 *  same kind of thing.
 *
 *  `reloadKey` lets the dashboard refetch after a new check-in without this
 *  component knowing anything about the form.
 */
export default function SelfReportTrend({ reloadKey = 0 }: { reloadKey?: number }) {
  const [reports, setReports] = useState<SelfReportPoint[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    setFailed(false);
    api
      .getSelfReportHistory(30)
      .then((res) => {
        if (live) setReports(res.reports);
      })
      .catch(() => {
        if (live) setFailed(true);
      });
    return () => {
      live = false;
    };
  }, [reloadKey]);

  // Two points is the minimum that makes a line mean anything; below that
  // the check-in card alone is the right surface, so show nothing here.
  if (failed) {
    return (
      <section className="panel p-5 mb-7">
        <h2 className="eyebrow mb-1.5">Your check-in trend</h2>
        <p role="alert" className="text-[12.5px] text-attention">
          Couldn't load your check-in history.
        </p>
      </section>
    );
  }
  if (reports.length < 2) return null;

  const latest = reports[reports.length - 1];

  return (
    <section className="panel p-5 mb-7">
      <h2 className="eyebrow mb-1.5">Your check-in trend</h2>
      <p className="text-[12.5px] text-text-faint mb-4">
        {reports.length} check-ins. Your own ratings over time — compared only to your own earlier
        answers.
      </p>
      <div className="space-y-3">
        {LINES.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between gap-4">
            <span className="text-[13px] font-medium w-24 shrink-0">{label}</span>
            <div className="flex-1 flex justify-end">
              <Sparkline values={reports.map((r) => r[key])} width={160} height={28} />
            </div>
            <span className="font-mono text-[12px] text-text-muted w-10 text-right shrink-0">
              {latest[key]}/5
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
