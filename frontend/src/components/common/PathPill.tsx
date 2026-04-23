import { Copy, Folder } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { copyToClipboard } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";

interface PathPillProps {
  path: string | null | undefined;
  label?: string;
  className?: string;
}

export function PathPill({ path, label, className }: PathPillProps) {
  const { toast } = useToast();
  if (!path) {
    return (
      <div
        className={`inline-flex items-center gap-2 rounded-md border border-dashed border-border/60 px-2 py-1 text-[11px] text-muted-foreground ${className ?? ""}`}>
        <Folder className="h-3.5 w-3.5" />
        <span>{label ?? "No local path yet"}</span>
      </div>
    );
  }
  const handleCopy = async () => {
    try {
      await copyToClipboard(path);
      toast({ title: "Path copied", description: path, variant: "success" });
    } catch {
      toast({ title: "Clipboard unavailable", variant: "destructive" });
    }
  };
  return (
    <div
      className={`inline-flex max-w-full items-center gap-1 rounded-md border border-border/70 bg-muted/20 px-2 py-1 font-mono text-[11px] ${className ?? ""}`}>
      <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="truncate text-foreground/80" title={path}>
        {path}
      </span>
      <Tooltip content="Copy path">
        <Button size="xs" variant="ghost" className="ml-0.5 h-5 w-5 p-0" onClick={handleCopy} aria-label="Copy path">
          <Copy className="h-3 w-3" />
        </Button>
      </Tooltip>
    </div>
  );
}
