import { ChevronDown, ChevronRight, FileWarning } from "lucide-react";
import { useState } from "react";

import { JobStatusBadge } from "@/components/common/StatusBadge";
import { Progress } from "@/components/ui/progress";
import { formatDateTime, formatJobKind, formatRelative, percent } from "@/lib/format";
import type { JobRecord } from "@/lib/types";
import { cn } from "@/lib/utils";

export function JobRow({ job }: { job: JobRecord }) {
  const [expanded, setExpanded] = useState(false);
  const failed = job.status === "failed";
  const running = job.status === "queued" || job.status === "running";
  const resultEntries = [
    typeof job.result.count === "number" ? { label: "Processed", value: job.result.count } : null,
    typeof job.result.downloaded_files === "number" ? { label: "Files", value: job.result.downloaded_files } : null,
    typeof job.result.failed_files === "number" ? { label: "Failed files", value: job.result.failed_files } : null,
    typeof job.result.skipped_files === "number" ? { label: "Skipped files", value: job.result.skipped_files } : null,
    typeof job.result.failed === "number" ? { label: "Failed", value: job.result.failed } : null,
    typeof job.result.skipped === "number" ? { label: "Skipped", value: job.result.skipped } : null,
  ].filter(Boolean) as { label: string; value: number }[];

  return (
    <div
      className={cn(
        "rounded-lg border bg-card/60 transition-colors",
        failed ? "border-destructive/40" : "border-border",
      )}>
      <button
        type="button"
        className="flex w-full items-center gap-3 p-3 text-left"
        onClick={() => setExpanded((prev) => !prev)}>
        <div className="text-muted-foreground">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{formatJobKind(job.kind)}</span>
            <JobStatusBadge value={job.status as never} />
            <span className="font-mono text-[11px] text-muted-foreground">{job.job_id.slice(0, 8)}</span>
            <span className="text-[11px] text-muted-foreground">{formatRelative(job.created_at)}</span>
          </div>
          <div className="text-xs text-muted-foreground truncate">
            {job.message || (running ? "Waiting…" : job.status === "completed" ? "Done" : "")}
          </div>
          {resultEntries.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {resultEntries.map((entry) => (
                <span
                  key={entry.label}
                  className="rounded border border-border/60 bg-muted/20 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {entry.label}: <span className="font-mono">{entry.value}</span>
                </span>
              ))}
              {typeof job.result.download_status === "string" && (
                <span className="rounded border border-border/60 bg-muted/20 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  Status: <span className="font-mono">{job.result.download_status}</span>
                </span>
              )}
            </div>
          )}
          {running && <Progress value={job.progress} />}
        </div>
        <div className="shrink-0 text-right">
          <div className="font-mono text-xs tabular-nums">{percent(job.progress)}</div>
        </div>
      </button>
      {expanded && (
        <div className="border-t border-border/60 px-3 py-3 text-xs space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Created</div>
              <div>{formatDateTime(job.created_at)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Started</div>
              <div>{formatDateTime(job.started_at)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Finished</div>
              <div>{formatDateTime(job.finished_at)}</div>
            </div>
          </div>
          {Object.keys(job.payload).length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Payload</div>
              <pre className="max-h-40 overflow-auto rounded bg-muted/40 p-2 font-mono text-[11px]">
                {JSON.stringify(job.payload, null, 2)}
              </pre>
            </div>
          )}
          {Object.keys(job.result).length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Result</div>
              <pre className="max-h-40 overflow-auto rounded bg-muted/40 p-2 font-mono text-[11px]">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </div>
          )}
          {job.error && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-2 text-destructive">
              <FileWarning className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <div className="font-medium">Error</div>
                <div className="text-destructive/90">{job.error}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
