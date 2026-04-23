import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { CategoryBadge } from "@/components/common/CategoryBadge";
import { DifficultyBadge } from "@/components/common/DifficultyBadge";
import { ChallengeStatusBadge, DownloadStatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Tooltip } from "@/components/ui/tooltip";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ChallengeRecord } from "@/lib/types";

export type ChallengeSortKey = "newest" | "oldest" | "title" | "difficulty" | "category" | "downloaded";

interface ChallengeTableProps {
  challenges: ChallengeRecord[];
  sort: ChallengeSortKey;
  selection: Set<number>;
  onSelectionChange: (next: Set<number>) => void;
  onRowClick?: (challenge: ChallengeRecord) => void;
  onDownload?: (challenge: ChallengeRecord) => void;
  activeId?: number | null;
  loading?: boolean;
}

const header = "px-3 py-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground";

function compare(a: ChallengeRecord, b: ChallengeRecord, key: ChallengeSortKey): number {
  switch (key) {
    case "title":
      return a.title.localeCompare(b.title);
    case "difficulty":
      return (a.difficulty ?? 99) - (b.difficulty ?? 99);
    case "category":
      return (a.category_display ?? a.category ?? "").localeCompare(b.category_display ?? b.category ?? "");
    case "downloaded":
      return Number(b.downloaded) - Number(a.downloaded);
    case "oldest":
      return a.challenge_id - b.challenge_id;
    case "newest":
    default:
      return b.challenge_id - a.challenge_id;
  }
}

export function ChallengeTable({
  challenges,
  sort,
  selection,
  onSelectionChange,
  onRowClick,
  onDownload,
  activeId,
  loading,
}: ChallengeTableProps) {
  const sorted = useMemo(() => [...challenges].sort((a, b) => compare(a, b, sort)), [challenges, sort]);
  const [hover, setHover] = useState<number | null>(null);

  const allSelected = sorted.length > 0 && sorted.every((c) => selection.has(c.challenge_id));
  const anySelected = sorted.some((c) => selection.has(c.challenge_id));

  const toggleAll = () => {
    const next = new Set(selection);
    if (allSelected) {
      sorted.forEach((c) => next.delete(c.challenge_id));
    } else {
      sorted.forEach((c) => next.add(c.challenge_id));
    }
    onSelectionChange(next);
  };

  const toggleRow = (id: number) => {
    const next = new Set(selection);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card/60">
      <div className="max-h-[calc(100vh-280px)] overflow-auto scrollbar-thin">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur">
            <tr className="border-b border-border">
              <th className={cn(header, "w-10 px-3")}>
                <Checkbox
                  aria-label="Select all visible"
                  checked={allSelected}
                  indeterminate={!allSelected && anySelected}
                  onChange={toggleAll}
                />
              </th>
              <th className={cn(header, "w-20")}>ID</th>
              <th className={cn(header, "min-w-[240px] text-left")}>Title</th>
              <th className={cn(header, "text-left")}>Category</th>
              <th className={cn(header, "text-left")}>Difficulty</th>
              <th className={cn(header, "text-left")}>Status</th>
              <th className={cn(header, "text-left")}>Download</th>
              <th className={cn(header, "text-left")}>Last activity</th>
              <th className={cn(header, "w-24 text-right pr-3")}></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((challenge) => {
              const selected = selection.has(challenge.challenge_id);
              const active = activeId === challenge.challenge_id;
              return (
                <tr
                  key={challenge.challenge_id}
                  className={cn(
                    "group cursor-pointer border-b border-border/40 transition-colors",
                    active ? "bg-primary/5" : hover === challenge.challenge_id ? "bg-muted/20" : "",
                  )}
                  onMouseEnter={() => setHover(challenge.challenge_id)}
                  onMouseLeave={() => setHover(null)}
                  onClick={() => onRowClick?.(challenge)}>
                  <td className="px-3 py-2.5" onClick={(event) => event.stopPropagation()}>
                    <Checkbox
                      aria-label={`Select ${challenge.title}`}
                      checked={selected}
                      onChange={() => toggleRow(challenge.challenge_id)}
                    />
                  </td>
                  <td className="px-3 py-2.5 font-mono text-xs text-muted-foreground">{challenge.challenge_id}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col">
                      <Link
                        to={`/challenges/${challenge.challenge_id}`}
                        className="truncate font-medium text-foreground transition-colors hover:text-primary"
                        onClick={(event) => event.stopPropagation()}>
                        {challenge.title}
                      </Link>
                      {challenge.author && (
                        <span className="truncate text-[11px] text-muted-foreground">
                          by {challenge.author}
                          {challenge.solvers !== null && challenge.solvers !== undefined
                            ? ` · ${challenge.solvers} solvers`
                            : ""}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <CategoryBadge category={challenge.category} display={challenge.category_display} />
                  </td>
                  <td className="px-3 py-2.5">
                    <DifficultyBadge value={challenge.difficulty} label={challenge.difficulty_label} />
                  </td>
                  <td className="px-3 py-2.5">
                    <ChallengeStatusBadge value={challenge.status as string} />
                  </td>
                  <td className="px-3 py-2.5">
                    <DownloadStatusBadge value={challenge.download_status as never} />
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">
                    <div>{formatRelative(challenge.last_crawled_at ?? challenge.last_seen)}</div>
                    <div className="text-[10px] text-muted-foreground/80">
                      {challenge.last_downloaded_at
                        ? `downloaded ${formatRelative(challenge.last_downloaded_at)}`
                        : challenge.last_seen
                          ? `seen ${formatRelative(challenge.last_seen)}`
                          : "never"}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right pr-3" onClick={(event) => event.stopPropagation()}>
                    {onDownload && (
                      <Tooltip content={challenge.downloaded ? "Re-download" : "Download"}>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 opacity-0 group-hover:opacity-100"
                          onClick={() => onDownload(challenge)}
                          aria-label="Download">
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                      </Tooltip>
                    )}
                  </td>
                </tr>
              );
            })}
            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-14 text-center text-sm text-muted-foreground">
                  No challenges match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
