import { useCallback } from "react";
import { Outlet } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { BackendStatusBanner } from "@/components/common/BackendStatusBanner";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function AppShell() {
  const queryClient = useQueryClient();
  const refresh = useCallback(() => {
    queryClient.invalidateQueries();
  }, [queryClient]);

  return (
    <div className="flex min-h-screen bg-background grid-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onGlobalRefresh={refresh} />
        <BackendStatusBanner />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto w-full max-w-[1440px] px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
