import { NavLink } from "react-router-dom";

import { navItems } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  return (
    <aside className="hidden h-screen w-[232px] shrink-0 border-r border-border bg-card/40 md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/20 text-primary">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 7h4v4h4V7h4v10h-4v-4h-4v4H6z" />
          </svg>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-tight">DreamHack</span>
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Local Console</span>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 scrollbar-thin">
        <ul className="space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  cn(
                    "group flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
                  )
                }>
                <Icon className="h-4 w-4" strokeWidth={2} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="border-t border-border p-4 text-[11px] leading-relaxed text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          <span>Local-only workspace</span>
        </div>
        <div className="mt-0.5">No cloud. No telemetry.</div>
      </div>
    </aside>
  );
}
