import { CheckCircle2, FileText, KeyRound, Loader2, ShieldAlert, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { SessionStatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useClearSession, useImportSession, useSession, useTestSession } from "@/hooks/useSession";
import { formatDateTime } from "@/lib/format";

export function SessionPage() {
  const session = useSession();
  const importSession = useImportSession();
  const clearSession = useClearSession();
  const testSession = useTestSession();
  const { toast } = useToast();

  const [cookieHeader, setCookieHeader] = useState("");
  const [cookieFile, setCookieFile] = useState("");

  const handleImportHeader = async () => {
    if (!cookieHeader.trim()) return;
    try {
      const result = await importSession.mutateAsync({ cookie_header: cookieHeader.trim() });
      toast({
        title: "Session updated",
        description: `Status: ${result.status}`,
        variant: result.authenticated ? "success" : "warning",
      });
      setCookieHeader("");
    } catch (err) {
      toast({
        title: "Import failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleImportFile = async () => {
    if (!cookieFile.trim()) return;
    try {
      const result = await importSession.mutateAsync({ cookie_file: cookieFile.trim() });
      toast({
        title: "Session imported from file",
        description: `Status: ${result.status}`,
        variant: result.authenticated ? "success" : "warning",
      });
      setCookieFile("");
    } catch (err) {
      toast({
        title: "Import failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleTest = async () => {
    try {
      const result = await testSession.mutateAsync();
      toast({
        title: `Session ${result.status}`,
        description: result.message || "Heuristic check complete.",
        variant: result.authenticated ? "success" : "warning",
      });
    } catch (err) {
      toast({
        title: "Test failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleClear = async () => {
    try {
      await clearSession.mutateAsync();
      toast({ title: "Session cleared", variant: "success" });
    } catch (err) {
      toast({
        title: "Clear failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const data = session.data;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Session"
        description="Manage the authenticated DreamHack cookies the backend uses when fetching."
      />

      <Card className="border-border/60 bg-card/50">
        <CardContent className="pt-6 text-sm text-muted-foreground">
          The tool only uses your own locally stored DreamHack session. If your account cannot access a challenge or
          file, the backend will fail normally and surface that error in the UI instead of bypassing access controls.
        </CardContent>
      </Card>

      {session.isLoading && <LoadingState rows={3} />}
      {session.isError && (
        <ErrorState title="Couldn't load session status" error={session.error} onRetry={() => session.refetch()} />
      )}

      {data && (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="h-4 w-4 text-primary" />
                Current session
              </CardTitle>
              <CardDescription>
                Session state is stored locally by the backend. Nothing is sent upstream.
              </CardDescription>
            </div>
            <SessionStatusBadge value={data.status} />
          </CardHeader>
          <CardContent className="grid gap-3 text-xs md:grid-cols-2">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Authenticated</div>
              <div className="mt-0.5 flex items-center gap-1">
                {data.authenticated ? (
                  <>
                    <ShieldCheck className="h-3.5 w-3.5 text-success" />
                    Yes
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-3.5 w-3.5 text-warning" />
                    No
                  </>
                )}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Has cookies</div>
              <div className="mt-0.5">{data.has_cookies ? "Yes" : "No"}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Last updated</div>
              <div className="mt-0.5">{formatDateTime(data.updated_at)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Last checked</div>
              <div className="mt-0.5">{formatDateTime(data.last_checked_at)}</div>
            </div>
            {data.cookie_names.length > 0 && (
              <div className="md:col-span-2">
                <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Cookie names</div>
                <div className="flex flex-wrap gap-1.5">
                  {data.cookie_names.map((name) => (
                    <span
                      key={name}
                      className="rounded-md border border-border/60 bg-muted/30 px-1.5 py-0.5 font-mono text-[11px]">
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {data.message && <div className="md:col-span-2 text-muted-foreground">{data.message}</div>}
            <div className="md:col-span-2 flex flex-wrap gap-2 pt-1">
              <Button size="sm" variant="outline" onClick={handleTest} disabled={testSession.isPending}>
                {testSession.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Test session
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleClear}
                disabled={clearSession.isPending || !data.has_cookies}>
                <Trash2 className="h-3.5 w-3.5" />
                Clear session
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Import cookie header</CardTitle>
            <CardDescription>
              Paste the value of the <code className="font-mono">Cookie</code> header from an authenticated DreamHack
              tab. Keys like <code className="font-mono">sessionid</code> are typically required.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label>Cookie header</Label>
            <Textarea
              rows={4}
              placeholder="sessionid=...; csrftoken=...; ..."
              value={cookieHeader}
              onChange={(e) => setCookieHeader(e.target.value)}
              className="font-mono text-xs"
            />
            <div className="flex justify-end">
              <Button size="sm" onClick={handleImportHeader} disabled={!cookieHeader.trim() || importSession.isPending}>
                {importSession.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                Import cookies
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Import cookie file</CardTitle>
            <CardDescription>
              The backend will read a local file (Netscape or JSON format) and load the cookies.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label>Absolute path to cookie file</Label>
            <Input
              placeholder="/Users/you/path/to/cookie.txt"
              value={cookieFile}
              onChange={(e) => setCookieFile(e.target.value)}
              className="font-mono text-xs"
            />
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="outline"
                onClick={handleImportFile}
                disabled={!cookieFile.trim() || importSession.isPending}>
                <FileText className="h-3.5 w-3.5" />
                Import file
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
