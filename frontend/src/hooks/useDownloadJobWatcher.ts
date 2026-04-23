import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/ui/toast";
import { queryKeys } from "@/lib/api";
import { useJob } from "@/hooks/useJobs";

interface DownloadJobWatcherOptions {
  jobId: string | null;
  onTerminal?: () => void;
}

function buildCompletedDescription(result: Record<string, unknown>): string {
  if (typeof result.local_path === "string" && result.local_path) {
    const status = typeof result.download_status === "string" ? result.download_status : "completed";
    const files = typeof result.downloaded_files === "number" ? result.downloaded_files : 0;
    const failed = typeof result.failed_files === "number" ? result.failed_files : 0;
    return `${status} · ${files} downloaded · ${failed} failed · ${result.local_path}`;
  }
  if (typeof result.succeeded === "number" || typeof result.failed === "number" || typeof result.skipped === "number") {
    return `succeeded ${result.succeeded ?? 0} · failed ${result.failed ?? 0} · skipped ${result.skipped ?? 0}`;
  }
  return "Job completed.";
}

export function useDownloadJobWatcher({ jobId, onTerminal }: DownloadJobWatcherOptions) {
  const job = useJob(jobId);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const handledKey = useRef<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      handledKey.current = null;
      return;
    }
    const data = job.data;
    if (!data) return;
    if (data.status !== "completed" && data.status !== "failed") return;

    const currentKey = `${jobId}:${data.status}`;
    if (handledKey.current === currentKey) return;
    handledKey.current = currentKey;

    queryClient.invalidateQueries({ queryKey: queryKeys.jobs() });
    queryClient.invalidateQueries({ queryKey: ["challenges"] });
    queryClient.invalidateQueries({ queryKey: ["challenge"] });
    queryClient.invalidateQueries({ queryKey: queryKeys.stats() });

    if (data.status === "completed") {
      const failed = typeof data.result.failed === "number" ? data.result.failed : 0;
      toast({
        title: "Download completed",
        description: buildCompletedDescription(data.result),
        variant: failed > 0 ? "warning" : "success",
      });
    } else {
      toast({
        title: "Download failed",
        description: data.error || data.message || "The backend reported a failure.",
        variant: "destructive",
      });
    }

    onTerminal?.();
  }, [job.data, jobId, onTerminal, queryClient, toast]);

  return job;
}
