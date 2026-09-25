export default function PageHeader({
  title,
  subtitle,
  status,
  note,
}: {
  title: string;
  subtitle?: string;
  status?: React.ReactNode;
  /** Quiet, secondary, updates on its own - e.g. when data last arrived. */
  note?: string;
}) {
  return (
    <header className="mb-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h1 className="text-[22px] font-semibold tracking-tight text-balance">{title}</h1>
        {status}
      </div>
      {subtitle && <p className="text-[13.5px] text-text-muted mt-1">{subtitle}</p>}
      {note && <p className="text-[11.5px] text-text-faint mt-1 font-mono">{note}</p>}
    </header>
  );
}
