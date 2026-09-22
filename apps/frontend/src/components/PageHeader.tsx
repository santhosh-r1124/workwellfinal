export default function PageHeader({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle?: string;
  status?: React.ReactNode;
}) {
  return (
    <header className="mb-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h1 className="text-[22px] font-semibold tracking-tight text-balance">{title}</h1>
        {status}
      </div>
      {subtitle && <p className="text-[13.5px] text-text-muted mt-1">{subtitle}</p>}
    </header>
  );
}
