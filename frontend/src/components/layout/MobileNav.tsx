import { Menu } from "lucide-react";
import { NavLink } from "react-router-dom";

import { navItems } from "@/components/layout/nav-items";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerDescription, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer";
import { cn } from "@/lib/utils";

export function MobileNav() {
  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open navigation">
          <Menu className="h-4 w-4" />
        </Button>
      </DrawerTrigger>
      <DrawerContent side="left" className="max-w-[320px]">
        <div className="border-b border-border px-5 py-4">
          <DrawerDescription className="text-[10px] uppercase tracking-[0.18em]">DreamHack</DrawerDescription>
          <DrawerTitle>Local Console</DrawerTitle>
        </div>
        <nav className="flex-1 overflow-y-auto p-4">
          <ul className="space-y-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
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
        <div className="border-t border-border px-4 py-3 text-[11px] text-muted-foreground">
          Local-only workspace. The backend owns downloads and filesystem writes.
        </div>
      </DrawerContent>
    </Drawer>
  );
}
