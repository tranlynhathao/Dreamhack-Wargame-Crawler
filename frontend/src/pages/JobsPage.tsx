import { Briefcase, RefreshCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { JobRow } from "@/components/jobs/JobRow";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useJobs } from "@/hooks/useJobs";
import type { JobStatus } from "@/lib/types";

export function JobsPage() {
  const jobs = useJobs();
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    const data = jobs.data ?? [];
    if (statusFilter === "all") return data;
    return data.filter((j) => j.status === statusFilter);
  }, [jobs.data, statusFilter]);

  const counts = useMemo(() => {
    const acc: Record<JobStatus, number> = {
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
    };
    (jobs.data ?? []).forEach((j) => {
      if (j.status in acc) {
        acc[j.status as JobStatus] += 1;
      }
    });
    return acc;
  }, [jobs.data]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Jobs"
        description="Background crawl and download operations. Updates in real time."
        actions={
          <Button size="sm" variant="outline" onClick={() => jobs.refetch()} disabled={jobs.isFetching}>
            <RefreshCcw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
            <span className="text-muted-foreground">Running</span>{" "}
            <span className="font-mono tabular-nums">{counts.running}</span>
          </div>
          <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
            <span className="text-muted-foreground">Queued</span>{" "}
            <span className="font-mono tabular-nums">{counts.queued}</span>
          </div>
          <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
            <span className="text-muted-foreground">Done</span>{" "}
            <span className="font-mono tabular-nums">{counts.completed}</span>
          </div>
          <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">
            <span className="text-muted-foreground">Failed</span>{" "}
            <span className="font-mono tabular-nums">{counts.failed}</span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-muted-foreground">Filter</span>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {jobs.isLoading && <LoadingState rows={5} />}
      {jobs.isError && <ErrorState title="Couldn't load jobs" error={jobs.error} onRetry={() => jobs.refetch()} />}
      {!jobs.isLoading && filtered.length === 0 && (
        <EmptyState
          icon={Briefcase}
          title="No jobs to show"
          description="Kick off a crawl or download to track progress here."
        />
      )}
      <div className="space-y-2">
        {filtered.map((job) => (
          <JobRow key={job.job_id} job={job} />
        ))}
      </div>
    </div>
  );
}
