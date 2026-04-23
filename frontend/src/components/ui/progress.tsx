import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  className?: string;
  indeterminate?: boolean;
  tone?: "default" | "success" | "warning" | "destructive";
}

const toneClass: Record<NonNullable<ProgressProps["tone"]>, string> = {
  default: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
};

export function Progress({ value, className, indeterminate, tone = "default" }: ProgressProps) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}>
      {indeterminate ? (
        <div className="absolute inset-y-0 left-0 w-1/3 animate-pulse rounded-full bg-primary/70" />
      ) : (
        <div
          className={cn("h-full rounded-full transition-[width]", toneClass[tone])}
          style={{ width: `${clamped * 100}%` }}
        />
      )}
    </div>
  );
}
