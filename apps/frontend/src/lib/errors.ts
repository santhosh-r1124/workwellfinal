/** What a caught request error is allowed to become on screen.
 *
 *  `api/client.ts` throws `Error("${status}: ${body}")`, so an unhandled
 *  catch rendered exactly that: "Error: 404: {"detail":"Not found"}" on a
 *  manager's screen. That is the "Error 500" the difference between a
 *  useful and useless failure message is about - raw status codes and raw
 *  JSON are not something anyone reading this app should have to parse.
 *
 *  The backend's `detail` field is already a short, hand-written domain
 *  message in every place that sets it deliberately (a taken email, an
 *  unimplemented connector) - see apps/backend/services/onboarding_service.py
 *  and integrations/base.py. Surfacing that text is an improvement, not a
 *  leak; what this strips is the status-code wrapper, and anything that
 *  doesn't parse as that shape at all (a network failure, a CORS error, a
 *  response with no body), which becomes a generic, honest sentence
 *  instead of a stack-shaped string.
 */
export function friendlyError(err: unknown, fallback = "Something went wrong. Please try again."): string {
  const message = err instanceof Error ? err.message : String(err ?? "");
  const match = /^(\d{3}):\s*([\s\S]*)$/.exec(message);
  if (!match) return fallback;

  const status = Number(match[1]);
  const body = match[2];

  let detail: string | undefined;
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === "string") detail = parsed.detail;
  } catch {
    // Not JSON - nothing here is safe to show verbatim.
  }

  if (status === 401 || status === 403) return "You're not authorized to do that.";
  if (status === 429) return "Too many requests right now — please wait a moment and try again.";
  if (status >= 500) return "The server had a problem handling that. Please try again.";
  return detail || fallback;
}
