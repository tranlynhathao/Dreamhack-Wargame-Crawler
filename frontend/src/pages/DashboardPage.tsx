import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  CircleDashed,
  Download,
  FileWarning,
  FolderTree,
  KeyRound,
  Loader2,
  Play,
  Plus,
  RefreshCcw,
  Settings2,
  ShieldAlert,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { CategoryBadge } from "@/components/common/CategoryBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { PathPill } from "@/components/common/PathPill";
import { SessionStatusBadge } from "@/components/common/StatusBadge";
import { StatCard } from "@/components/common/StatCard";
import { JobRow } from "@/components/jobs/JobRow";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input, Label } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { useCrawlChallenge, useCrawlSync, useExportManifest, useSyncFiles } from "@/hooks/useChallenges";
import { useJobs } from "@/hooks/useJobs";
import { useSession } from "@/hooks/useSession";
import { useSettings } from "@/hooks/useSettings";
import { useStats } from "@/hooks/useStats";
import { CATEGORY_OPTIONS } from "@/lib/types";

export function DashboardPage() {
  const stats = useStats();
  const session = useSession();
  const settings = useSettings();
  const jobs = useJobs();
  const crawlSync = useCrawlSync();
  const crawlChallenge = useCrawlChallenge();
  const syncFiles = useSyncFiles();
  const exportManifest = useExportManifest();
  const { toast } = useToast();
  const [syncingAll, setSyncingAll] = useState(false);
  const [crawlOpen, setCrawlOpen] = useState(false);
  const [crawlIdentifier, setCrawlIdentifier] = useState("");

  const totalChallenges = stats.data?.challenges_total ?? 0;
  const downloaded = stats.data?.challenges_downloaded ?? 0;
  const notDownloaded = Math.max(0, totalChallenges - downloaded);
  const withFiles = stats.data?.challenges_with_files ?? 0;

  const recentJobs = (jobs.data ?? []).slice(0, 6);

  const categorySorted = useMemo(() => {
    if (!stats.data) return [] as [string, number][];
    return Object.entries(stats.data.categories).sort((a, b) => b[1] - a[1]);
  }, [stats.data]);
  const difficultySorted = useMemo(() => {
    if (!stats.data) return [] as [string, number][];
    return Object.entries(stats.data.difficulties).sort((a, b) => {
      const aValue = a[0] === "unknown" ? Number.MAX_SAFE_INTEGER : Number(a[0]);
      const bValue = b[0] === "unknown" ? Number.MAX_SAFE_INTEGER : Number(b[0]);
      return aValue - bValue;
    });
  }, [stats.data]);

  const categoryTotal = categorySorted.reduce((acc, [, n]) => acc + n, 0) || 1;
  const difficultyTotal = difficultySorted.reduce((acc, [, n]) => acc + n, 0) || 1;

  const sessionInvalid = session.data && session.data.status !== "valid";
  const workspaceMissing = settings.data && !settings.data.workspace_root;

  const handleCrawlAll = async () => {
    try {
      setSyncingAll(true);
      await crawlSync.mutateAsync({});
      toast({
        title: "Crawl sync queued",
        description: "Backend is fetching the full challenge index.",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Could not start crawl",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSyncingAll(false);
    }
  };

  const handleSyncFiles = async () => {
    try {
      const result = await syncFiles.mutateAsync();
      const parts = Object.entries(result)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" · ");
      toast({
        title: "Workspace reconciled",
        description: parts || "Completed",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Sync failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleCrawlSingle = async () => {
    if (!crawlIdentifier.trim()) return;
    try {
      const job = await crawlChallenge.mutateAsync({ identifier: crawlIdentifier.trim() });
      toast({
        title: "Single challenge crawl queued",
        description: `Job ${job.job_id.slice(0, 8)} · target: ${crawlIdentifier.trim()}`,
        variant: "success",
      });
      setCrawlIdentifier("");
      setCrawlOpen(false);
    } catch (err) {
      toast({
        title: "Could not queue crawl",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleExportManifest = async () => {
    try {
      const result = await exportManifest.mutateAsync();
      toast({
        title: "Manifest exported",
        description: result.path,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Export failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  if (stats.isError) {
    return <ErrorState title="Failed to load stats" error={stats.error} onRetry={() => stats.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your local DreamHack workspace and backend state."
        actions={
          <>
            <Button size="sm" variant="outline" onClick={handleSyncFiles} disabled={syncFiles.isPending}>
              {syncFiles.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCcw className="h-3.5 w-3.5" />
              )}
              Reconcile workspace
            </Button>
            <Button size="sm" onClick={handleCrawlAll} disabled={syncingAll || crawlSync.isPending}>
              {crawlSync.isPending || syncingAll ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              Sync metadata
            </Button>
          </>
        }
      />

      {(sessionInvalid || workspaceMissing) && (
        <div className="grid gap-3 md:grid-cols-2">
          {sessionInvalid && (
            <Card className="border-warning/40 bg-warning/10">
              <CardContent className="flex items-start gap-3 p-4">
                <ShieldAlert className="h-5 w-5 text-warning" />
                <div className="flex-1 space-y-1">
                  <div className="text-sm font-medium text-foreground">Session not valid</div>
                  <div className="text-xs text-muted-foreground">
                    Some crawl/download calls will fail without an authenticated session.
                  </div>
                  <Button asChild variant="outline" size="xs" className="mt-1">
                    <Link to="/session">
                      <KeyRound className="h-3 w-3" />
                      Fix session
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
          {workspaceMissing && (
            <Card className="border-destructive/40 bg-destructive/10">
              <CardContent className="flex items-start gap-3 p-4">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <div className="flex-1 space-y-1">
                  <div className="text-sm font-medium text-foreground">Workspace root not set</div>
                  <div className="text-xs text-muted-foreground">
                    Configure where the backend should save challenge folders.
                  </div>
                  <Button asChild variant="outline" size="xs" className="mt-1">
                    <Link to="/settings">
                      <FolderTree className="h-3 w-3" />
                      Open settings
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total challenges"
          icon={Boxes}
          value={stats.isLoading ? "…" : totalChallenges}
          hint={`${withFiles} have attachments`}
        />
        <StatCard
          title="Downloaded"
          icon={CheckCircle2}
          tone="success"
          value={stats.isLoading ? "…" : downloaded}
          hint={totalChallenges ? `${Math.round((downloaded / totalChallenges) * 100)}% of inventory` : "—"}
        />
        <StatCard
          title="Not downloaded"
          icon={CircleDashed}
          tone="warning"
          value={stats.isLoading ? "…" : notDownloaded}
          hint="Ready for bulk download"
        />
        <StatCard
          title="Session"
          icon={KeyRound}
          tone={session.data?.status === "valid" ? "success" : "warning"}
          value={session.isLoading ? "…" : session.data ? <SessionStatusBadge value={session.data.status} /> : "—"}
          hint={session.data?.message || "—"}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Button size="sm" onClick={handleCrawlAll} disabled={syncingAll || crawlSync.isPending}>
            {crawlSync.isPending || syncingAll ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCcw className="h-3.5 w-3.5" />
            )}
            Sync challenge metadata
          </Button>
          <Button size="sm" variant="outline" onClick={() => setCrawlOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Crawl one challenge
          </Button>
          <Button size="sm" variant="outline" onClick={handleExportManifest} disabled={exportManifest.isPending}>
            {exportManifest.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Export manifest
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link to="/settings">
              <Settings2 className="h-3.5 w-3.5" />
              Open settings
            </Link>
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent jobs</CardTitle>
            <Button asChild size="xs" variant="ghost">
              <Link to="/jobs">View all</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {jobs.isLoading && <LoadingState rows={3} />}
            {jobs.isError && (
              <ErrorState title="Couldn't load jobs" error={jobs.error} onRetry={() => jobs.refetch()} />
            )}
            {!jobs.isLoading && recentJobs.length === 0 && (
              <EmptyState
                icon={Download}
                title="No background jobs yet"
                description="Trigger a sync or a download to see it tracked here."
              />
            )}
            {recentJobs.map((job) => (
              <JobRow key={job.job_id} job={job} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Workspace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Root path</div>
              <PathPill path={settings.data?.workspace_root} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Database</div>
              <PathPill path={settings.data?.database_path} />
            </div>
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Manifest export</div>
              <PathPill path={settings.data?.manifest_export_path} />
            </div>
            {settings.isError && (
              <div className="flex items-center gap-2 text-destructive">
                <FileWarning className="h-3.5 w-3.5" />
                Couldn't load settings
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Category distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.isLoading && <LoadingState rows={4} />}
            {!stats.isLoading && categorySorted.length === 0 && (
              <EmptyState
                icon={Boxes}
                title="No challenges indexed yet"
                description="Run a metadata sync to populate your local inventory."
              />
            )}
            <div className="space-y-2">
              {categorySorted.map(([key, count]) => {
                const display = CATEGORY_OPTIONS.find((c) => c.value === key)?.label ?? key;
                const share = count / categoryTotal;
                return (
                  <div key={key} className="flex items-center gap-3 text-xs">
                    <CategoryBadge category={key} display={display} />
                    <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted/40">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-primary/70"
                        style={{ width: `${Math.max(2, share * 100)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right font-mono tabular-nums text-muted-foreground">{count}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Difficulty distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.isLoading && <LoadingState rows={4} />}
            {!stats.isLoading && difficultySorted.length === 0 && (
              <EmptyState
                icon={Boxes}
                title="No difficulty data yet"
                description="Difficulty buckets will appear after the backend indexes metadata."
              />
            )}
            <div className="space-y-2">
              {difficultySorted.map(([key, count]) => {
                const share = count / difficultyTotal;
                const label = key === "unknown" ? "Unknown" : `Level ${key}`;
                return (
                  <div key={key} className="flex items-center gap-3 text-xs">
                    <span className="w-20 rounded-md border border-border/60 bg-muted/20 px-2 py-1 font-mono text-[11px]">
                      {label}
                    </span>
                    <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted/40">
                      <div
                        className="absolute inset-y-0 left-0 rounded-full bg-primary/70"
                        style={{ width: `${Math.max(2, share * 100)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right font-mono tabular-nums text-muted-foreground">{count}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={crawlOpen} onOpenChange={setCrawlOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crawl a single challenge</DialogTitle>
            <DialogDescription>
              Provide a DreamHack challenge ID or a full challenge URL. The backend will fetch metadata into the local
              inventory.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label>Challenge ID or URL</Label>
            <Input
              placeholder="1234 or https://dreamhack.io/wargame/challenges/1234"
              value={crawlIdentifier}
              onChange={(event) => setCrawlIdentifier(event.target.value)}
              autoFocus
              onKeyDown={(event) => {
                if (event.key === "Enter") handleCrawlSingle();
              }}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button size="sm" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button
              size="sm"
              onClick={handleCrawlSingle}
              disabled={!crawlIdentifier.trim() || crawlChallenge.isPending}>
              {crawlChallenge.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              Queue crawl
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
