import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { SupportResource } from "../types";

const CATEGORY_LABEL: Record<string, string> = {
  crisis: "If you need help now",
  counselling: "Talk to someone",
  benefits: "Benefits & perks",
  general: "Other support",
};

/** Where the employee can turn for help, as published by their org. A plain
 *  directory, not a recommendation: the dashboard can point somewhere real
 *  instead of ending at "consider reaching out". Shows nothing when the org
 *  has published nothing, rather than inventing a placeholder. */
export default function SupportResources() {
  const [resources, setResources] = useState<SupportResource[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    api
      .getSupportResources()
      .then((res) => {
        if (live) setResources(res.resources);
      })
      .catch(() => {
        if (live) setFailed(true);
      });
    return () => {
      live = false;
    };
  }, []);

  if (failed) {
    return (
      <section className="panel p-5 mb-7">
        <h2 className="eyebrow mb-1.5">Support</h2>
        <p role="alert" className="text-[12.5px] text-attention">
          Couldn't load support resources.
        </p>
      </section>
    );
  }
  if (resources.length === 0) return null;

  // Group in display order; the API already sorts crisis first.
  const groups: { category: string; items: SupportResource[] }[] = [];
  for (const r of resources) {
    const last = groups[groups.length - 1];
    if (last && last.category === r.category) last.items.push(r);
    else groups.push({ category: r.category, items: [r] });
  }

  return (
    <section className="panel p-5 mb-7">
      <h2 className="eyebrow mb-3">Support</h2>
      <div className="space-y-5">
        {groups.map((group) => (
          <div key={group.category}>
            <p className="text-[11px] uppercase tracking-[0.06em] text-text-faint mb-2">
              {CATEGORY_LABEL[group.category] || group.category}
            </p>
            <div className="space-y-2.5">
              {group.items.map((r) => (
                <div
                  key={r.id}
                  className={`rounded-lg border px-3.5 py-3 ${
                    r.category === "crisis"
                      ? "border-accent/30 bg-accent-ghost/40"
                      : "border-line bg-surface-sunken"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-[13.5px] font-medium">{r.label}</span>
                    <div className="flex items-center gap-3 shrink-0">
                      {/* A real number/email becomes a tap-to-call / mailto
                          link; a plain-text placeholder like "Company number"
                          is shown as text so it never produces a broken link. */}
                      {r.phone &&
                        (/\d/.test(r.phone) ? (
                          <a
                            href={`tel:${r.phone}`}
                            className="font-mono text-[12px] text-accent hover:underline underline-offset-2"
                          >
                            {r.phone}
                          </a>
                        ) : (
                          <span className="text-[12px] text-text-muted">{r.phone}</span>
                        ))}
                      {r.email &&
                        (r.email.includes("@") ? (
                          <a
                            href={`mailto:${r.email}`}
                            className="text-[12px] text-accent hover:underline underline-offset-2"
                          >
                            {r.email}
                          </a>
                        ) : (
                          <span className="text-[12px] text-text-muted">{r.email}</span>
                        ))}
                      {r.url && (
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[12px] text-accent hover:underline underline-offset-2"
                        >
                          Open ↗
                        </a>
                      )}
                    </div>
                  </div>
                  {r.description && (
                    <p className="text-[12.5px] text-text-muted mt-1 leading-relaxed">
                      {r.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
