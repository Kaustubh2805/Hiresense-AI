import { useId, type ButtonHTMLAttributes, type ReactNode } from "react";

type Tone = "brand" | "neutral" | "success" | "warning" | "danger";

const toneClasses: Record<Tone, string> = {
  brand: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  neutral: "border-slate-700/60 bg-slate-800/40 text-slate-300",
  success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  danger: "border-rose-500/30 bg-rose-500/10 text-rose-300",
};

export function Button({
  children,
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet";
}) {
  const variantClass = {
    primary: "border border-blue-500/50 bg-blue-600 text-white shadow-sm hover:bg-blue-500 active:bg-blue-700",
    secondary: "border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-750 hover:border-slate-600",
    quiet: "border border-transparent bg-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/60",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${variantClass} ${className}`}
    >
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-slate-800 bg-[#101522] ${className}`}>
      {children}
    </section>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function Chip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return <Badge tone={tone} className="font-normal">{children}</Badge>;
}

export function ProgressRing({
  value,
  label,
  size = 80,
  stroke = 6,
}: {
  value: number | null;
  label?: string;
  size?: number;
  stroke?: number;
}) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const normalized = value === null ? 0 : Math.max(0, Math.min(10, value)) / 10;
  return (
    <div className="relative inline-grid shrink-0 place-items-center" role="img" aria-label={label ?? `Score ${value === null ? "not available" : `${value.toFixed(1)} out of 10`}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgb(255 255 255 / 8%)" strokeWidth={stroke} />
        {value !== null && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#2563eb"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - normalized)}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        )}
      </svg>
      <span className="absolute text-sm font-semibold text-slate-100">
        {value === null ? "—" : value.toFixed(1)}
      </span>
    </div>
  );
}

export function ProgressBar({
  value,
  label,
  className = "",
}: {
  value: number | null;
  label?: string;
  className?: string;
}) {
  const safeValue = value === null ? 0 : Math.max(0, Math.min(10, value)) * 10;
  return (
    <div
      className={`h-1.5 overflow-hidden rounded bg-slate-800 ${className}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={10}
      aria-valuenow={value ?? undefined}
      aria-valuetext={value === null ? "Not analysed" : undefined}
    >
      {value !== null && <div className="h-full rounded bg-blue-600 transition-[width]" style={{ width: `${safeValue}%` }} />}
    </div>
  );
}

export function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-[#101522] p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-white">{value}</p>
      {detail && <p className="mt-1 text-xs text-slate-400">{detail}</p>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton rounded ${className}`} />;
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-[#101522] px-6 py-12 text-center">
      <h2 className="text-base font-semibold text-slate-200">{title}</h2>
      <div className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-400">{children}</div>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-col justify-between gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-end">
      <div>
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">{eyebrow}</p>}
        <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-white sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm leading-normal text-slate-400">{description}</p>}
      </div>
      {action}
    </header>
  );
}

export function Tabs({
  tabs,
  value,
  onChange,
}: {
  tabs: string[];
  value: string;
  onChange: (tab: string) => void;
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1.5">
      {tabs.map((tab) => (
        <button
          key={tab}
          role="tab"
          aria-selected={value === tab}
          type="button"
          onClick={() => onChange(tab)}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${value === tab ? "border border-blue-500/40 bg-blue-600/15 text-blue-300" : "border border-slate-800 bg-slate-850 text-slate-400 hover:bg-slate-800 hover:text-slate-200"}`}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
