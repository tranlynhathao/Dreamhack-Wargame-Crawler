import { BookOpenText, Moon, RefreshCcw, Sun } from "lucide-react";

import { MobileNav } from "@/components/layout/MobileNav";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { api } from "@/lib/api";

export function Topbar({ onGlobalRefresh }: { onGlobalRefresh?: () => void }) {
  const { toggle, resolved } = useTheme();
  const { isError, isFetching } = useBackendHealth();

  const ok = !isError;

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-6 backdrop-blur">
      <MobileNav />
      <div className="flex flex-col leading-tight md:hidden">
        <span className="text-xs font-semibold tracking-tight">DreamHack</span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Local Console</span>
      </div>
      <div className="flex items-center gap-2">
        <div
          className={`flex h-2 w-2 rounded-full ${ok ? "bg-success" : "bg-destructive"} ${isFetching ? "animate-pulse" : ""}`}
        />
        <div className="flex flex-col leading-tight">
          <span className="text-xs font-medium">{ok ? "Backend online" : "Backend offline"}</span>
          <span className="text-[10px] font-mono text-muted-foreground">{api.baseUrl}</span>
        </div>
      </div>
      <div className="ml-auto flex items-center gap-1">
        {onGlobalRefresh && (
          <Tooltip content="Refresh current view">
            <Button variant="ghost" size="icon" onClick={onGlobalRefresh} aria-label="Refresh">
              <RefreshCcw className="h-4 w-4" />
            </Button>
          </Tooltip>
        )}
        <Tooltip content={resolved === "dark" ? "Switch to light" : "Switch to dark"}>
          <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
            {resolved === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </Tooltip>
        <Tooltip content="Open local API docs">
          <Button variant="ghost" size="icon" asChild aria-label="Open local API docs">
            <a href={`${api.baseUrl}/docs`} target="_blank" rel="noopener noreferrer">
              <BookOpenText className="h-4 w-4" />
            </a>
          </Button>
        </Tooltip>
      </div>
    </header>
  );
}
