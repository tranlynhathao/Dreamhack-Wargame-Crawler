import { ArrowLeft, ExternalLink } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { CategoryBadge } from "@/components/common/CategoryBadge";
import { DifficultyBadge } from "@/components/common/DifficultyBadge";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PathPill } from "@/components/common/PathPill";
import { ChallengeStatusBadge, DownloadStatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { useChallengeDetail, useDownloadChallenge } from "@/hooks/useChallenges";
import { useDownloadJobWatcher } from "@/hooks/useDownloadJobWatcher";
import { useOpenFolder, useSettings } from "@/hooks/useSettings";
import { formatBytes, formatDateTime, formatRelative } from "@/lib/format";
import type { DownloadMode } from "@/lib/types";
import { copyToClipboard, openExternal } from "@/lib/utils";

export function ChallengeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const detail = useChallengeDetail(id);
  const settings = useSettings();
  const download = useDownloadChallenge();
  const openFolder = useOpenFolder();
  const { toast } = useToast();
  const [jobId, setJobId] = useState<string | null>(null);

  const trackedJob = useDownloadJobWatcher({
    jobId,
    onTerminal: () => {
      setJobId(null);
      void detail.refetch();
    },
  });
  const jobRunning = trackedJob.data?.status === "queued" || trackedJob.data?.status === "running";

  if (detail.isLoading) {
    return (
      <div className="max-w-4xl">
        <LoadingState rows={8} />
      </div>
    );
  }
  if (detail.isError || !detail.data) {
    return <ErrorState title="Couldn't load challenge" error={detail.error} onRetry={() => detail.refetch()} />;
  }

  const { challenge } = detail.data;

  const runDownload = async (mode: DownloadMode) => {
    try {
      const job = await download.mutateAsync({ id: challenge.challenge_id, mode });
      setJobId(job.job_id);
      toast({
        title: "Download queued",
        description: `Job ${job.job_id.slice(0, 8)} · saving to local workspace`,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Could not queue download",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const runOpenFolder = async () => {
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
    <div className="space-y-5">
      <Button size="xs" variant="ghost" onClick={() => navigate(-1)}>
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </Button>

      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-xs text-muted-foreground">#{challenge.challenge_id}</div>
          <h1 className="text-2xl font-semibold tracking-tight">{challenge.title}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <CategoryBadge category={challenge.category} display={challenge.category_display} />
            <DifficultyBadge value={challenge.difficulty} label={challenge.difficulty_label} />
            <ChallengeStatusBadge value={challenge.status as string} />
            <DownloadStatusBadge value={challenge.download_status as never} />
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => runDownload("resume")} disabled={download.isPending || jobRunning}>
            Download
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => runDownload("overwrite")}
            disabled={download.isPending || jobRunning}>
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
          <Button size="sm" variant="outline" onClick={runOpenFolder} disabled={openFolder.isPending}>
            Open folder
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            {challenge.description_html ? (
              <div className="description-html" dangerouslySetInnerHTML={{ __html: challenge.description_html }} />
            ) : challenge.description_text ? (
              <pre className="whitespace-pre-wrap text-sm text-foreground/90">{challenge.description_text}</pre>
            ) : (
              <p className="text-sm text-muted-foreground">No description available.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Local workspace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Workspace root</div>
              <PathPill path={settings.data?.workspace_root} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Challenge folder</div>
              <PathPill path={challenge.local_path} />
            </div>
            <Button
              size="xs"
              variant="outline"
              onClick={async () => {
                if (!challenge.local_path) return;
                try {
                  await copyToClipboard(challenge.local_path);
                  toast({ title: "Folder path copied", variant: "success" });
                } catch {
                  toast({ title: "Clipboard unavailable", variant: "destructive" });
                }
              }}
              disabled={!challenge.local_path}>
              Copy folder path
            </Button>
            <Button
              size="xs"
              variant="outline"
              onClick={async () => {
                if (!challenge.url) return;
                try {
                  await copyToClipboard(challenge.url);
                  toast({ title: "Challenge URL copied", variant: "success" });
                } catch {
                  toast({ title: "Clipboard unavailable", variant: "destructive" });
                }
              }}
              disabled={!challenge.url}>
              Copy challenge URL
            </Button>
            <p className="text-[11px] text-muted-foreground">
              Downloads are written by the local backend — your browser does not save anything.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Metadata</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
          <Field label="Local status" value={challenge.download_status.replaceAll("_", " ")} />
          <Field label="Author" value={challenge.author ?? "—"} />
          <Field
            label="Solvers"
            value={challenge.solvers !== null && challenge.solvers !== undefined ? String(challenge.solvers) : "—"}
          />
          <Field label="First seen" value={formatDateTime(challenge.first_seen)} />
          <Field label="Last seen" value={formatRelative(challenge.last_seen)} />
          <Field label="Last crawled" value={formatRelative(challenge.last_crawled_at)} />
          <Field label="Last downloaded" value={formatRelative(challenge.last_downloaded_at)} />
          <Field label="Slug" value={challenge.slug || "—"} />
          <Field label="Has attachments" value={challenge.has_attachments ? "Yes" : "No"} />
          <Field label="Files" value={`${challenge.file_count}`} />
          <Field label="Bytes" value={formatBytes(challenge.byte_count)} />
        </CardContent>
      </Card>

      {(challenge.parse_warnings.length > 0 || challenge.last_error) && (
        <Card className="border-warning/40 bg-warning/5">
          <CardHeader>
            <CardTitle>Warnings & errors</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            {challenge.last_error && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-destructive">
                <strong>Last error:</strong> {challenge.last_error}
              </div>
            )}
            {challenge.parse_warnings.length > 0 && (
              <ul className="list-disc pl-5 text-muted-foreground">
                {challenge.parse_warnings.map((warn, i) => (
                  <li key={i}>{warn}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {jobRunning && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="pt-6 text-xs text-muted-foreground">
            {trackedJob.data?.message || "Download job is running in the backend."}
          </CardContent>
        </Card>
      )}

      {detail.data.files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Files · {detail.data.files.length}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-xs">
            {detail.data.files.map((f) => (
              <div
                key={`${f.challenge_id}-${f.filename}`}
                className="flex items-center justify-between rounded-md border border-border/60 bg-muted/10 p-2">
                <div className="min-w-0">
                  <div className="truncate font-mono">{f.filename}</div>
                  <div className="truncate text-[10px] text-muted-foreground">{f.relative_path}</div>
                </div>
                <div className="text-[10px] text-muted-foreground">{f.size_bytes ?? "—"}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div>
        <Button size="xs" variant="ghost" asChild>
          <Link to="/challenges">← Back to challenges</Link>
        </Button>
      </div>
    </div>
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
