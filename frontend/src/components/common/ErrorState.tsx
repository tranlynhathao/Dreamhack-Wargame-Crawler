import { AlertTriangle, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}

function formatError(error: unknown): string {
  if (!error) return "Unknown error.";
  if (error instanceof Error) return error.message;
  return String(error);
}

export function ErrorState({ title = "Something went wrong.", error, onRetry, className }: ErrorStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center ${className ?? ""}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/15 text-destructive">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <div className="space-y-1">
        <div className="text-sm font-medium text-foreground">{title}</div>
        <div className="text-xs text-muted-foreground max-w-lg break-words">{formatError(error)}</div>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCcw className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}
