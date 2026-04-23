import { Boxes, Download, Loader2, Play, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { ChallengeDetailDrawer } from "@/components/challenges/ChallengeDetailDrawer";
import {
  ChallengeFilters,
  DEFAULT_FILTERS,
  type ChallengeFiltersState,
} from "@/components/challenges/ChallengeFilters";
import { ChallengeTable } from "@/components/challenges/ChallengeTable";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useBulkDownload, useChallenges, useCrawlChallenge, useDownloadChallenge } from "@/hooks/useChallenges";
import { useDownloadJobWatcher } from "@/hooks/useDownloadJobWatcher";
import { useSettings } from "@/hooks/useSettings";
import type { ChallengeListParams, ChallengeRecord, DownloadMode } from "@/lib/types";

function filtersToParams(f: ChallengeFiltersState): ChallengeListParams {
  return {
    search: f.search || undefined,
    category: f.category === "all" ? undefined : f.category,
    difficulty: f.difficulty === "all" ? undefined : Number(f.difficulty),
    status: f.status === "all" ? undefined : f.status,
    downloaded: f.downloaded === "yes" ? true : f.downloaded === "no" ? false : undefined,
    limit: 1000,
    offset: 0,
  };
}

export function ChallengesPage() {
  const [filters, setFilters] = useState<ChallengeFiltersState>(DEFAULT_FILTERS);
  const [selection, setSelection] = useState<Set<number>>(new Set());
  const [activeId, setActiveId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkMode, setBulkMode] = useState<DownloadMode>("resume");
  const [crawlOpen, setCrawlOpen] = useState(false);
  const [crawlIdentifier, setCrawlIdentifier] = useState("");
  const [downloadJobId, setDownloadJobId] = useState<string | null>(null);
  const [bulkJobId, setBulkJobId] = useState<string | null>(null);

  const params = useMemo(() => filtersToParams(filters), [filters]);
  const challenges = useChallenges(params);
  const settings = useSettings();
  const download = useDownloadChallenge();
  const bulkDownload = useBulkDownload();
  const crawlChallenge = useCrawlChallenge();
  const { toast } = useToast();

  useDownloadJobWatcher({
    jobId: downloadJobId,
    onTerminal: () => {
      setDownloadJobId(null);
      void challenges.refetch();
    },
  });
  useDownloadJobWatcher({
    jobId: bulkJobId,
    onTerminal: () => {
      setBulkJobId(null);
      void challenges.refetch();
    },
  });

  const handleOpen = (challenge: ChallengeRecord) => {
    setActiveId(challenge.challenge_id);
    setDrawerOpen(true);
  };

  const handleDownloadOne = async (challenge: ChallengeRecord, mode: DownloadMode = "resume") => {
    try {
      const job = await download.mutateAsync({ id: challenge.challenge_id, mode });
      setDownloadJobId(job.job_id);
      toast({
        title: `Queued ${challenge.title}`,
        description: `Backend will save into the workspace folder. Job ${job.job_id.slice(0, 8)}.`,
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

  const handleBulkDownload = async () => {
    try {
      const job = await bulkDownload.mutateAsync({
        category: params.category ?? undefined,
        difficulty: params.difficulty ?? undefined,
        status: params.status ?? undefined,
        downloaded: params.downloaded ?? undefined,
        search: params.search ?? undefined,
        mode: bulkMode,
      });
      setBulkJobId(job.job_id);
      toast({
        title: "Bulk download queued",
        description: `Job ${job.job_id.slice(0, 8)} · mode: ${bulkMode}`,
        variant: "success",
      });
      setBulkOpen(false);
    } catch (err) {
      toast({
        title: "Bulk download failed to start",
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
        title: "Crawl queued",
        description: `Job ${job.job_id.slice(0, 8)} · target: ${crawlIdentifier.trim()}`,
        variant: "success",
      });
      setCrawlIdentifier("");
      setCrawlOpen(false);
    } catch (err) {
      toast({
        title: "Crawl failed to start",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const countLabel = challenges.data?.length === 1 ? "1 challenge" : `${challenges.data?.length ?? 0} challenges`;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Challenges"
        description="Browse, filter, and download your local inventory."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setCrawlOpen(true)}>
              <Plus className="h-3.5 w-3.5" />
              Crawl single
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!challenges.data || challenges.data.length === 0}
              onClick={() => setBulkOpen(true)}>
              <Download className="h-3.5 w-3.5" />
              Download filtered
            </Button>
          </>
        }
      />

      <ChallengeFilters value={filters} onChange={setFilters} />

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <span>{countLabel}</span>
          {selection.size > 0 && (
            <span className="rounded-md border border-border/60 bg-muted/20 px-2 py-0.5 text-[11px]">
              {selection.size} selected
            </span>
          )}
        </div>
        {selection.size > 0 && (
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="outline"
              onClick={async () => {
                const ids = Array.from(selection);
                const pending = ids.map((id) => download.mutateAsync({ id, mode: "resume" }));
                try {
                  const results = await Promise.allSettled(pending);
                  const success = results.filter((r) => r.status === "fulfilled").length;
                  const failed = results.length - success;
                  toast({
                    title: `${success} queued`,
                    description: failed ? `${failed} failed to start` : "Each download runs as its own job.",
                    variant: failed ? "warning" : "success",
                  });
                } catch (err) {
                  toast({
                    title: "Selection download failed",
                    description: err instanceof Error ? err.message : "Unknown error",
                    variant: "destructive",
                  });
                }
              }}>
              <Play className="h-3 w-3" />
              Download selected
            </Button>
            <Button size="xs" variant="ghost" onClick={() => setSelection(new Set())}>
              <Trash2 className="h-3 w-3" />
              Clear
            </Button>
          </div>
        )}
      </div>

      {challenges.isLoading && <LoadingState rows={10} />}
      {challenges.isError && (
        <ErrorState title="Couldn't load challenges" error={challenges.error} onRetry={() => challenges.refetch()} />
      )}
      {!challenges.isLoading && !challenges.isError && (challenges.data?.length ?? 0) === 0 && (
        <EmptyState
          icon={Boxes}
          title="No challenges match your filters"
          description="Reset filters or run a metadata sync to populate this view."
          action={
            <Button size="sm" variant="outline" onClick={() => setFilters(DEFAULT_FILTERS)}>
              Reset filters
            </Button>
          }
        />
      )}
      {!challenges.isLoading && (challenges.data?.length ?? 0) > 0 && (
        <ChallengeTable
          challenges={challenges.data ?? []}
          sort={filters.sort}
          selection={selection}
          onSelectionChange={setSelection}
          onRowClick={handleOpen}
          onDownload={(c) => handleDownloadOne(c, c.downloaded ? "overwrite" : "resume")}
          activeId={activeId}
        />
      )}

      <ChallengeDetailDrawer
        id={activeId}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        workspaceRoot={settings.data?.workspace_root}
      />

      <ConfirmDialog
        open={bulkOpen}
        onOpenChange={setBulkOpen}
        title="Download everything matching the current filters?"
        description={
          <>
            This asks the backend to download <strong>{countLabel}</strong> into your local workspace. Your browser does
            not download anything.
            <div className="mt-3 space-y-1">
              <Label>Mode</Label>
              <Select value={bulkMode} onValueChange={(v) => setBulkMode(v as DownloadMode)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="resume">Resume — skip already downloaded files</SelectItem>
                  <SelectItem value="skip">Skip — only new challenges</SelectItem>
                  <SelectItem value="overwrite">Overwrite — re-fetch everything</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        }
        confirmText="Queue bulk download"
        onConfirm={handleBulkDownload}
      />

      <Dialog open={crawlOpen} onOpenChange={setCrawlOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crawl a single challenge</DialogTitle>
            <DialogDescription>
              Provide a challenge ID (e.g., <code className="font-mono">1234</code>) or its DreamHack URL.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label>Identifier</Label>
            <Input
              placeholder="1234 or https://dreamhack.io/wargame/challenges/1234"
              value={crawlIdentifier}
              onChange={(e) => setCrawlIdentifier(e.target.value)}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCrawlSingle();
              }}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">
                Cancel
              </Button>
            </DialogClose>
            <Button size="sm" onClick={handleCrawlSingle} disabled={!crawlIdentifier.trim()}>
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
