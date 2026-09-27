/** The three things that are not data.
 *
 *  These were being improvised per screen, and one of them was improvised
 *  wrongly: a failed request rendered the same sentence as an empty result,
 *  so "we could not reach the server" and "you have no pattern history yet"
 *  were indistinguishable. The second is reassuring and the first is not,
 *  which is exactly the difference an employee needs.
 *
 *  Kept deliberately plain. A spinner on every panel makes a page look busy
 *  rather than fast, so loading is a skeleton of the shape that is coming.
 */

export function Skeleton({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`panel p-5 space-y-3 ${className}`} aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="h-3 rounded bg-[var(--glass-bg-strong)] animate-pulse"
          style={{ width: `${90 - i * 14}%` }}
        />
      ))}
    </div>
  );
}

/** A failure the reader can act on: what broke, and a way to try again.
 *  Never the raw status code or the backend's message - those leak
 *  internals and mean nothing to the person reading them. */
export function ErrorState({
  message = "Couldn't load this just now.",
  onRetry,
  className = "",
}: {
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`panel border-attention/30 p-5 ${className}`}
      style={{ background: "var(--attention-ghost)" }}
    >
      <p className="text-[13.5px] text-attention">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-quiet mt-3">
          Try again
        </button>
      )}
    </div>
  );
}

/** Nothing here, and why — which is not the same as something going wrong. */
export function EmptyState({
  title,
  children,
  className = "",
}: {
  title: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`panel px-5 py-8 text-center ${className}`}>
      <p className="text-[13.5px] font-medium">{title}</p>
      {children && <p className="text-[12.5px] text-text-muted mt-1.5 max-w-sm mx-auto">{children}</p>}
    </div>
  );
}
