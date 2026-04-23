import { Badge } from "@/components/ui/badge";
import { CATEGORY_OPTIONS } from "@/lib/types";

const colorMap: Record<string, string> = {
  misc: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  crypto: "bg-purple-500/15 text-purple-300 border-purple-500/30",
  web: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  web3: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30",
  pwnable: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  forensics: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  reversing: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  cloud: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
};

export function CategoryBadge({ category, display }: { category: string | null | undefined; display?: string | null }) {
  if (!category) {
    return <Badge variant="subtle">Uncategorized</Badge>;
  }
  const label = display ?? CATEGORY_OPTIONS.find((c) => c.value === category)?.label ?? category;
  const color = colorMap[category] ?? colorMap.misc;
  return (
    <div
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-wide ${color}`}>
      {label}
    </div>
  );
}
