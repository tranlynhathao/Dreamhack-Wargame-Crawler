import { cn } from "@/lib/utils";

interface DifficultyBadgeProps {
  value: number | null | undefined;
  label?: string | null;
  className?: string;
}

function toneFor(value: number) {
  if (value <= 2) return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  if (value <= 4) return "bg-sky-500/15 text-sky-300 border-sky-500/30";
  if (value <= 6) return "bg-amber-500/15 text-amber-300 border-amber-500/30";
  if (value <= 8) return "bg-orange-500/15 text-orange-300 border-orange-500/30";
  return "bg-rose-500/15 text-rose-300 border-rose-500/30";
}

export function DifficultyBadge({ value, label, className }: DifficultyBadgeProps) {
  if (value === null || value === undefined) {
    return <span className={cn("text-xs text-muted-foreground", className)}>—</span>;
  }
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-mono font-medium tabular-nums",
        toneFor(value),
        className,
      )}>
      <span className="opacity-60">Lv</span>
      <span>{label ?? value}</span>
    </div>
  );
}
