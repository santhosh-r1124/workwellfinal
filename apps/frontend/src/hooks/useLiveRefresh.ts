import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { LiveStatus } from "../types";

const POLL_MS = 20_000;

/** Keeps a page current without reloading it.
 *
 *  Polls a cheap version token rather than the dashboard's real payload:
 *  refetching baselines, history, patterns and interventions every twenty
 *  seconds would be four queries and a re-render for the overwhelmingly
 *  common case of nothing having changed. `reload` fires only when the
 *  token moves.
 *
 *  Also refetches when the tab regains focus, because the interesting
 *  case is coming back to a page left open since this morning - and
 *  pauses while hidden, since a backgrounded tab polling all night is
 *  load with nobody to show it to. */
export function useLiveRefresh(reload: () => void, enabled = true) {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const lastVersion = useRef<string | null>(null);
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const check = async () => {
      if (document.hidden) return;
      try {
        const next = await api.liveStatus();
        if (cancelled) return;
        setStatus(next);
        if (lastVersion.current !== null && lastVersion.current !== next.version) {
          reloadRef.current();
        }
        lastVersion.current = next.version;
      } catch {
        // A failed poll is not worth surfacing: what is on screen is still
        // the last known good state, and the next tick retries.
      }
    };

    check();
    const timer = window.setInterval(check, POLL_MS);
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [enabled]);

  return status;
}
