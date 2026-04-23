import { useQuery } from "@tanstack/react-query";

import { api, queryKeys } from "@/lib/api";
import type { JobRecord } from "@/lib/types";

function hasActiveJob(jobs: JobRecord[] | undefined): boolean {
  if (!jobs) return false;
  return jobs.some((job) => job.status === "queued" || job.status === "running");
}

export function useJobs() {
  return useQuery({
    queryKey: queryKeys.jobs(),
    queryFn: () => api.listJobs(),
    refetchInterval: (query) => (hasActiveJob(query.state.data) ? 1_000 : 5_000),
  });
}

export function useJob(jobId: string | undefined | null) {
  return useQuery({
    queryKey: jobId ? queryKeys.job(jobId) : ["job", "none"],
    queryFn: () => api.getJob(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const job = query.state.data;
      if (!job) return 2_000;
      return job.status === "queued" || job.status === "running" ? 1_000 : false;
    },
  });
}
