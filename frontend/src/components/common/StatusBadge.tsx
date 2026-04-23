import { CheckCircle2, Circle, CircleDashed, Loader2, ShieldAlert, ShieldCheck, ShieldX, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ChallengeStatus, DownloadStatus, JobStatus, SessionStatus } from "@/lib/types";

interface StatusBadgeProps<T extends string> {
  value: T | string | null | undefined;
  label?: string;
  className?: string;
}

const sessionMap: Record<
  SessionStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"]; icon: JSX.Element }
> = {
  valid: { label: "Valid", variant: "success", icon: <ShieldCheck className="h-3 w-3" /> },
  invalid: { label: "Invalid", variant: "destructive", icon: <ShieldX className="h-3 w-3" /> },
  missing: { label: "Missing", variant: "subtle", icon: <ShieldAlert className="h-3 w-3" /> },
  unknown: { label: "Unknown", variant: "outline", icon: <ShieldAlert className="h-3 w-3" /> },
};

const jobMap: Record<
  JobStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"]; icon: JSX.Element }
> = {
  queued: { label: "Queued", variant: "subtle", icon: <CircleDashed className="h-3 w-3" /> },
  running: { label: "Running", variant: "default", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  completed: { label: "Completed", variant: "success", icon: <CheckCircle2 className="h-3 w-3" /> },
  failed: { label: "Failed", variant: "destructive", icon: <XCircle className="h-3 w-3" /> },
};

const challengeMap: Record<
  ChallengeStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"]; icon: JSX.Element }
> = {
  todo: { label: "Todo", variant: "outline", icon: <Circle className="h-3 w-3" /> },
  attempted: { label: "Attempted", variant: "warning", icon: <CircleDashed className="h-3 w-3" /> },
  solved: { label: "Solved", variant: "success", icon: <CheckCircle2 className="h-3 w-3" /> },
};

export function SessionStatusBadge({ value }: StatusBadgeProps<SessionStatus>) {
  const entry = sessionMap[(value as SessionStatus) ?? "unknown"] ?? sessionMap.unknown;
  return (
    <Badge variant={entry.variant}>
      {entry.icon}
      {entry.label}
    </Badge>
  );
}

export function JobStatusBadge({ value }: StatusBadgeProps<JobStatus>) {
  const entry = jobMap[(value as JobStatus) ?? "queued"] ?? jobMap.queued;
  return (
    <Badge variant={entry.variant}>
      {entry.icon}
      {entry.label}
    </Badge>
  );
}

export function ChallengeStatusBadge({ value }: StatusBadgeProps<ChallengeStatus>) {
  if (!value) return <span className="text-xs text-muted-foreground">—</span>;
  const entry = challengeMap[value as ChallengeStatus];
  if (!entry)
    return (
      <Badge variant="outline">
        <Circle className="h-3 w-3" />
        {value}
      </Badge>
    );
  return (
    <Badge variant={entry.variant}>
      {entry.icon}
      {entry.label}
    </Badge>
  );
}

export function DownloadBadge({ downloaded, hasAttachments }: { downloaded: boolean; hasAttachments: boolean }) {
  if (downloaded) {
    return (
      <Badge variant="success">
        <CheckCircle2 className="h-3 w-3" />
        Downloaded
      </Badge>
    );
  }
  if (!hasAttachments) {
    return (
      <Badge variant="subtle">
        <Circle className="h-3 w-3" />
        Metadata only
      </Badge>
    );
  }
  return (
    <Badge variant="outline">
      <Circle className="h-3 w-3" />
      Not downloaded
    </Badge>
  );
}

const downloadStatusMap: Record<
  DownloadStatus,
  { label: string; variant: React.ComponentProps<typeof Badge>["variant"]; icon: JSX.Element }
> = {
  not_downloaded: { label: "Not downloaded", variant: "outline", icon: <Circle className="h-3 w-3" /> },
  metadata_only: { label: "Metadata only", variant: "subtle", icon: <Circle className="h-3 w-3" /> },
  description_saved: { label: "Description saved", variant: "default", icon: <CheckCircle2 className="h-3 w-3" /> },
  files_downloaded: { label: "Files downloaded", variant: "success", icon: <CheckCircle2 className="h-3 w-3" /> },
  partial: { label: "Partial download", variant: "warning", icon: <CircleDashed className="h-3 w-3" /> },
  failed: { label: "Failed", variant: "destructive", icon: <XCircle className="h-3 w-3" /> },
};

export function DownloadStatusBadge({ value }: StatusBadgeProps<DownloadStatus>) {
  const entry = downloadStatusMap[(value as DownloadStatus) ?? "not_downloaded"] ?? downloadStatusMap.not_downloaded;
  return (
    <Badge variant={entry.variant}>
      {entry.icon}
      {entry.label}
    </Badge>
  );
}
