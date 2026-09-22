/** Trend of the real daily series. Endpoint is emphasised because "where it
 *  ended up" is the value the rest of the row is about. */
export default function Sparkline({
  values,
  className = "",
  width = 96,
  height = 24,
}: {
  values: number[];
  className?: string;
  width?: number;
  height?: number;
}) {
  const clean = values.filter((v) => Number.isFinite(v));
  if (clean.length < 2) return null;

  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const pad = 2;

  const points = clean.map((v, i) => {
    const x = pad + (i / (clean.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });

  const line = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${points[points.length - 1][0].toFixed(1)},${height} L${points[0][0].toFixed(1)},${height} Z`;
  const [lastX, lastY] = points[points.length - 1];
  const gradientId = `spark-${clean.length}-${Math.round(min)}-${Math.round(max)}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradientId})`} />
      <path d={line} fill="none" stroke="var(--accent)" strokeWidth="1.4" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="2.4" fill="var(--accent)" />
    </svg>
  );
}
