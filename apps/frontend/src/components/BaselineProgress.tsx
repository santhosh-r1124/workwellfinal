import { Link } from "react-router-dom";

import type { BaselineReadiness } from "../types";
import Icon from "./Icon";

/** What the first week or two actually looks like.
 *
 *  Every real employee spends 7-14 days here before there is anything to
 *  compare against, and the screen used to say "no sustained deviation
 *  from your baseline" - which reads as "we checked, you are fine" when
 *  nothing had been measured at all. Saying so plainly is both more
 *  honest and the only way someone knows they still need to connect
 *  something. */
export default function BaselineProgress({ readiness }: { readiness: BaselineReadiness }) {
  const { state, measured_days: measured, required_days: required } = readiness;
  const pct = Math.min(100, Math.round((measured / Math.max(1, required)) * 100));
  const remaining = Math.max(0, required - measured);

  if (state === "no_data") {
    return (
      <section className="panel p-5 mb-7">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-ghost text-accent">
            <Icon name="spark" className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold">Nothing is reporting yet</h2>
            <p className="text-[13px] text-text-muted mt-1">
              WorkWell has no measurements for you, so there is nothing it can say. It compares you
              only against your own history, and that history does not exist until something starts
              sending.
            </p>
            <ul className="mt-3 space-y-1.5 text-[13px] text-text-muted">
              <li>
                <Link to="/privacy" className="text-accent underline underline-offset-2 decoration-1 hover:decoration-2">
                  Register a device
                </Link>{" "}
                and run the agent on the machine you work on.
              </li>
              <li>
                Optionally{" "}
                <Link to="/privacy" className="text-accent underline underline-offset-2 decoration-1 hover:decoration-2">
                  connect a calendar
                </Link>{" "}
                for meeting load.
              </li>
              <li>Check what you are sharing — everything is off unless you allow it.</li>
            </ul>
            <p className="text-[12px] text-text-faint mt-3">
              After that it needs {required} days of your own data before it will say anything at
              all. The quiet first week is the product working, not failing.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="panel p-5 mb-7">
      {/* The percentage rides the heading rather than the paragraph: wrapped
          onto its own line on a phone, it read as a stray number floating
          above the bar. */}
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[15px] font-semibold">Learning your normal</h2>
        <span className="chip border-line text-text-muted font-mono shrink-0">{pct}%</span>
      </div>
      <p className="text-[13px] text-text-muted mt-1">
        {measured} of {required} days measured.{" "}
        {remaining > 0
          ? `${remaining} more before there is enough of your own history to compare against.`
          : "Almost there."}
      </p>

      <div
        style={{ background: "var(--glass-bg-sunken)" }}
        className="mt-3.5 h-1.5 w-full overflow-hidden rounded-full border border-[var(--glass-border)]"
        role="progressbar"
        aria-valuenow={measured}
        aria-valuemin={0}
        aria-valuemax={required}
        aria-label="Baseline progress"
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-500"
          style={{ width: `${Math.max(4, pct)}%` }}
        />
      </div>

      <p className="text-[12px] text-text-faint mt-3">
        Nothing is flagged during this period — not because you are fine, but because there is not
        yet anything to compare today against. Your check-in below still counts.
      </p>
    </section>
  );
}
