import { ServerOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { api } from "@/lib/api";
import { copyToClipboard } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";

export function BackendStatusBanner() {
  const { isError, refetch, fetchStatus } = useBackendHealth();
  const { toast } = useToast();

  if (!isError) return null;

  const command = `python3 dreamhack_crawler.py serve --host 127.0.0.1 --port 8000`;

  return (
    <div className="border-b border-destructive/30 bg-destructive/10 text-destructive-foreground">
      <div className="mx-auto flex max-w-[1440px] items-center gap-3 px-4 py-2 text-xs">
        <ServerOff className="h-4 w-4 text-destructive" />
        <div className="flex-1 leading-snug">
          <span className="font-medium text-foreground">Backend unreachable.</span>{" "}
          <span className="text-muted-foreground">
            Couldn't reach <code className="rounded bg-muted/40 px-1 py-0.5 font-mono">{api.baseUrl}</code>. Start the
            local API:
          </span>{" "}
          <code className="rounded bg-muted/60 px-1.5 py-0.5 font-mono text-foreground">{command}</code>
        </div>
        <Button
          size="xs"
          variant="outline"
          onClick={async () => {
            try {
              await copyToClipboard(command);
              toast({ title: "Command copied", variant: "success" });
            } catch {
              /* no-op */
            }
          }}>
          Copy
        </Button>
        <Button size="xs" variant="outline" onClick={() => refetch()} disabled={fetchStatus === "fetching"}>
          Retry
        </Button>
      </div>
    </div>
  );
}
