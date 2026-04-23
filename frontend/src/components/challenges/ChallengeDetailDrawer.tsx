import { AlertTriangle, Download, ExternalLink, FileText, Loader2, RefreshCcw } from "lucide-react";
import { useState } from "react";

import { CategoryBadge } from "@/components/common/CategoryBadge";
import { DifficultyBadge } from "@/components/common/DifficultyBadge";
import { PathPill } from "@/components/common/PathPill";
import { ChallengeStatusBadge, DownloadStatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerDescription, DrawerTitle } from "@/components/ui/drawer";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/components/ui/toast";
import { useChallengeDetail, useDownloadChallenge } from "@/hooks/useChallenges";
import { useDownloadJobWatcher } from "@/hooks/useDownloadJobWatcher";
import { useOpenFolder } from "@/hooks/useSettings";
import { formatBytes, formatDateTime, formatRelative } from "@/lib/format";
import type { DownloadMode } from "@/lib/types";
import { copyToClipboard, openExternal } from "@/lib/utils";

interface ChallengeDetailDrawerProps {
  id: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceRoot?: string | null;
}

export function ChallengeDetailDrawer({ id, open, onOpenChange, workspaceRoot }: ChallengeDetailDrawerProps) {
  const { data, isLoading, isError, error, refetch } = useChallengeDetail(id);
  const download = useDownloadChallenge();
  const openFolder = useOpenFolder();
  const { toast } = useToast();
  const [jobId, setJobId] = useState<string | null>(null);

  const trackedJob = useDownloadJobWatcher({
    jobId,
    onTerminal: () => {
      setJobId(null);
      void refetch();
    },
  });
  const jobRunning = trackedJob.data?.status === "queued" || trackedJob.data?.status === "running";

  const challenge = data?.challenge;

  const triggerDownload = async (mode: DownloadMode) => {
    if (!challenge) return;
    try {
      const job = await download.mutateAsync({ id: challenge.challenge_id, mode });
      setJobId(job.job_id);
      toast({
        title: `${mode === "overwrite" ? "Re-download" : "Download"} queued`,
        description: `Job ${job.job_id.slice(0, 8)} · backend will save files to the workspace folder.`,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Download failed to start",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const triggerOpenFolder = async () => {
    if (!challenge) return;
    try {
      const result = await openFolder.mutateAsync({ challenge_id: String(challenge.challenge_id) });
      toast({
        title: "Opened local folder",
        description: result.path,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Could not open folder",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="flex flex-col">
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <DrawerDescription className="font-mono">#{challenge?.challenge_id ?? id ?? "—"}</DrawerDescription>
            <DrawerTitle className="truncate">{challenge?.title ?? (isLoading ? "Loading…" : "Challenge")}</DrawerTitle>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin px-5 py-4 space-y-5">
          {isError && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
              {error instanceof Error ? error.message : "Failed to load challenge."}
              <Button size="xs" variant="outline" className="ml-2" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          )}

          {challenge && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <CategoryBadge category={challenge.category} display={challenge.category_display} />
                <DifficultyBadge value={challenge.difficulty} label={challenge.difficulty_label} />
                <ChallengeStatusBadge value={challenge.status as string} />
                <DownloadStatusBadge value={challenge.download_status as never} />
              </div>

              <section className="rounded-lg border border-border bg-muted/10 p-4 space-y-2">
                <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Local workspace
                </div>
                {workspaceRoot && (
                  <div className="text-xs text-muted-foreground">
                    Workspace root: <span className="font-mono text-foreground/80">{workspaceRoot}</span>
                  </div>
                )}
                <PathPill path={challenge.local_path} />
                <p className="text-[11px] text-muted-foreground">
                  When you trigger a download, the backend writes into this local folder. Your browser does not download
                  anything.
                </p>
              </section>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <Field label="Local status" value={challenge.download_status.replaceAll("_", " ")} />
                <Field label="Author" value={challenge.author ?? "—"} />
                <Field
                  label="Solvers"
                  value={
                    challenge.solvers !== null && challenge.solvers !== undefined ? String(challenge.solvers) : "—"
                  }
                />
                <Field label="First seen" value={formatDateTime(challenge.first_seen)} />
                <Field label="Last seen" value={formatRelative(challenge.last_seen)} />
                <Field label="Last crawled" value={formatRelative(challenge.last_crawled_at)} />
                <Field label="Last downloaded" value={formatRelative(challenge.last_downloaded_at)} />
                <Field label="Files" value={`${challenge.file_count}`} />
                <Field label="Bytes" value={formatBytes(challenge.byte_count)} />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => triggerDownload("resume")} disabled={download.isPending || jobRunning}>
                  {download.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}
                  {challenge.downloaded ? "Sync download" : "Download"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => triggerDownload("overwrite")}
                  disabled={download.isPending || jobRunning}>
                  <RefreshCcw className="h-3.5 w-3.5" />
                  Re-download
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => challenge.url && openExternal(challenge.url)}
                  disabled={!challenge.url}>
                  <ExternalLink className="h-3.5 w-3.5" />
                  Open on DreamHack
                </Button>
                <Button size="sm" variant="outline" onClick={triggerOpenFolder} disabled={openFolder.isPending}>
                  Open folder
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    if (!challenge.local_path) return;
                    try {
                      await copyToClipboard(challenge.local_path);
                      toast({
                        title: "Folder path copied",
                        description: challenge.local_path,
                        variant: "success",
                      });
                    } catch {
                      toast({ title: "Clipboard unavailable", variant: "destructive" });
                    }
                  }}
                  disabled={!challenge.local_path}>
                  Copy folder path
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    if (!challenge.url) return;
                    try {
                      await copyToClipboard(challenge.url);
                      toast({
                        title: "Challenge URL copied",
                        description: challenge.url,
                        variant: "success",
                      });
                    } catch {
                      toast({ title: "Clipboard unavailable", variant: "destructive" });
                    }
                  }}
                  disabled={!challenge.url}>
                  Copy URL
                </Button>
              </div>

              {(challenge.parse_warnings.length > 0 || challenge.last_error) && (
                <div className="space-y-2">
                  {challenge.last_error && (
                    <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
                      <AlertTriangle className="mt-0.5 h-4 w-4" />
                      <div>
                        <div className="font-medium">Last error</div>
                        <div className="text-destructive/90">{challenge.last_error}</div>
                      </div>
                    </div>
                  )}
                  {challenge.parse_warnings.length > 0 && (
                    <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-xs">
                      <div className="mb-1 font-medium text-warning">Parse warnings</div>
                      <ul className="list-disc space-y-0.5 pl-4 text-muted-foreground">
                        {challenge.parse_warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {jobRunning && (
                <div className="rounded-md border border-primary/30 bg-primary/5 p-3 text-xs text-muted-foreground">
                  {trackedJob.data?.message || "Download job is running in the backend."}
                </div>
              )}

              <Separator />

              <section>
                <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Description
                </div>
                {challenge.description_html ? (
                  <div className="description-html" dangerouslySetInnerHTML={{ __html: challenge.description_html }} />
                ) : challenge.description_text ? (
                  <pre className="whitespace-pre-wrap text-xs text-foreground/90">{challenge.description_text}</pre>
                ) : (
                  <p className="text-xs text-muted-foreground">No description available.</p>
                )}
              </section>

              {data && data.files.length > 0 && (
                <section>
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Files · {data.files.length}
                    </div>
                  </div>
                  <div className="space-y-1">
                    {data.files.map((file) => (
                      <div
                        key={`${file.challenge_id}-${file.filename}`}
                        className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/10 p-2 text-xs">
                        <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <div className="min-w-0 flex-1">
                          <div className="truncate font-mono text-foreground/90">{file.filename}</div>
                          <div className="truncate text-[10px] text-muted-foreground">{file.relative_path}</div>
                        </div>
                        <div className="text-[10px] text-muted-foreground">{formatBytes(file.size_bytes)}</div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="truncate text-foreground/90">{value}</div>
    </div>
  );
}
