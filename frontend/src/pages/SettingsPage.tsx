import { Activity, Download, FolderOpen, FolderTree, Loader2, Save, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { PathPill } from "@/components/common/PathPill";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useTheme as useThemeProvider } from "@/components/theme/ThemeProvider";
import { useExportManifest, useSyncFiles } from "@/hooks/useChallenges";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { useOpenFolder, useRunDoctor, useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { api } from "@/lib/api";
import type { DoctorIssue } from "@/lib/types";

export function SettingsPage() {
  const settings = useSettings();
  const update = useUpdateSettings();
  const exportManifest = useExportManifest();
  const syncFiles = useSyncFiles();
  const runDoctor = useRunDoctor();
  const openFolder = useOpenFolder();
  const health = useBackendHealth();
  const { theme, setTheme } = useThemeProvider();
  const { toast } = useToast();
  const [doctorIssues, setDoctorIssues] = useState<DoctorIssue[]>([]);

  const [form, setForm] = useState({
    workspace_root: "",
    request_delay_seconds: "1",
    max_retries: "3",
    timeout_seconds: "30",
    log_level: "INFO",
  });

  useEffect(() => {
    if (!settings.data) return;
    setForm({
      workspace_root: settings.data.workspace_root ?? "",
      request_delay_seconds: String(settings.data.request_delay_seconds ?? 1),
      max_retries: String(settings.data.max_retries ?? 3),
      timeout_seconds: String(settings.data.timeout_seconds ?? 30),
      log_level: settings.data.log_level ?? "INFO",
    });
  }, [settings.data]);

  const handleSave = async () => {
    try {
      await update.mutateAsync({
        workspace_root: form.workspace_root || undefined,
        request_delay_seconds: Number(form.request_delay_seconds),
        max_retries: Number(form.max_retries),
        timeout_seconds: Number(form.timeout_seconds),
        log_level: form.log_level || undefined,
      });
      toast({ title: "Settings saved", variant: "success" });
    } catch (err) {
      toast({
        title: "Save failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleExport = async () => {
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

  const handleSyncFiles = async () => {
    try {
      const result = await syncFiles.mutateAsync();
      const parts = Object.entries(result)
        .map(([key, value]) => `${key}: ${value}`)
        .join(" · ");
      toast({
        title: "Workspace synced",
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

  const handleDoctor = async () => {
    try {
      const report = await runDoctor.mutateAsync();
      setDoctorIssues(report.issues);
      const errorCount = report.issues.filter((issue) => issue.severity === "error").length;
      const warningCount = report.issues.filter((issue) => issue.severity === "warning").length;
      toast({
        title: "Doctor completed",
        description: `${errorCount} errors · ${warningCount} warnings`,
        variant: errorCount ? "warning" : "success",
      });
    } catch (err) {
      toast({
        title: "Doctor failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleOpenWorkspace = async () => {
    if (!settings.data?.workspace_root) return;
    try {
      const result = await openFolder.mutateAsync({ path: settings.data.workspace_root });
      toast({
        title: "Opened workspace",
        description: result.path,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Could not open workspace",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleTestBackend = async () => {
    try {
      await api.health();
      void health.refetch();
      toast({
        title: "Backend reachable",
        description: `${api.baseUrl}/api/health`,
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Backend unreachable",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  if (settings.isLoading) return <LoadingState rows={5} />;
  if (settings.isError) {
    return <ErrorState title="Couldn't load settings" error={settings.error} onRetry={() => settings.refetch()} />;
  }
  if (!settings.data) return null;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Settings"
        description="Configure where the backend stores files and how politely it talks to DreamHack."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={handleTestBackend} disabled={health.isFetching}>
              <Activity className="h-3.5 w-3.5" />
              Test backend
            </Button>
            <Button size="sm" variant="outline" onClick={handleExport} disabled={exportManifest.isPending}>
              <Download className="h-3.5 w-3.5" />
              Export manifest
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>Control plane</CardTitle>
          <CardDescription>
            These actions all go through the local backend. The browser does not write files to disk directly.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Button size="sm" variant="outline" onClick={handleSyncFiles} disabled={syncFiles.isPending}>
            {syncFiles.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FolderTree className="h-3.5 w-3.5" />
            )}
            Sync files
          </Button>
          <Button size="sm" variant="outline" onClick={handleDoctor} disabled={runDoctor.isPending}>
            {runDoctor.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldAlert className="h-3.5 w-3.5" />
            )}
            Run doctor
          </Button>
          <Button size="sm" variant="outline" onClick={handleOpenWorkspace} disabled={openFolder.isPending}>
            <FolderOpen className="h-3.5 w-3.5" />
            Open workspace
          </Button>
          <Button size="sm" variant="outline" onClick={handleExport} disabled={exportManifest.isPending}>
            <Download className="h-3.5 w-3.5" />
            Export manifest
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderTree className="h-4 w-4 text-primary" />
            Workspace
          </CardTitle>
          <CardDescription>
            Absolute path where the backend writes challenge folders. The UI never writes to disk directly.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label>Workspace root</Label>
            <Input
              className="font-mono text-xs"
              value={form.workspace_root}
              onChange={(e) => setForm((prev) => ({ ...prev, workspace_root: e.target.value }))}
              placeholder="/Users/you/Projects/Dreamhack"
            />
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground">Current:</span>
            <PathPill path={settings.data.workspace_root} />
          </div>
          <div className="grid gap-3 pt-1 md:grid-cols-2">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Database</div>
              <PathPill path={settings.data.database_path} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Manifest export</div>
              <PathPill path={settings.data.manifest_export_path} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Backend API</div>
              <PathPill path={api.baseUrl} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">DreamHack base URL</div>
              <PathPill path={settings.data.base_url} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Crawl behaviour</CardTitle>
          <CardDescription>
            Conservative defaults. The backend will retry with backoff, so you rarely need to crank these up.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Request delay (s)</Label>
            <Input
              type="number"
              step="0.1"
              min="0"
              value={form.request_delay_seconds}
              onChange={(e) => setForm((prev) => ({ ...prev, request_delay_seconds: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Max retries</Label>
            <Input
              type="number"
              min="0"
              value={form.max_retries}
              onChange={(e) => setForm((prev) => ({ ...prev, max_retries: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Timeout (s)</Label>
            <Input
              type="number"
              min="1"
              value={form.timeout_seconds}
              onChange={(e) => setForm((prev) => ({ ...prev, timeout_seconds: e.target.value }))}
            />
          </div>
          <div className="space-y-1.5 md:col-span-3">
            <Label>Log level</Label>
            <Select value={form.log_level} onValueChange={(v) => setForm((prev) => ({ ...prev, log_level: v }))}>
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DEBUG">DEBUG</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARNING">WARNING</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>UI-only preferences stored in the browser for this local console.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-1.5">
          <Label>Theme</Label>
          <Select value={theme} onValueChange={(value) => setTheme(value as typeof theme)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Doctor report</CardTitle>
          <CardDescription>
            Validation output from the backend. Use this to spot mismatches between the database and local workspace.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {doctorIssues.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No report loaded yet. Run <strong>Doctor</strong> to inspect local consistency.
            </div>
          ) : (
            doctorIssues.map((issue, index) => (
              <div
                key={`${issue.code}-${index}`}
                className="rounded-md border border-border/60 bg-muted/10 p-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="rounded border border-border/60 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider">
                    {issue.severity}
                  </span>
                  <span className="font-medium">{issue.code}</span>
                  {issue.challenge_id ? (
                    <span className="font-mono text-muted-foreground">#{issue.challenge_id}</span>
                  ) : null}
                </div>
                <div className="mt-1 text-muted-foreground">{issue.message}</div>
                {issue.path ? <PathPill path={issue.path} /> : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={update.isPending}>
          {update.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          Save changes
        </Button>
      </div>
    </div>
  );
}
