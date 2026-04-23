import { Briefcase, Cog, Gauge, KeyRound, Layers, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/challenges", label: "Challenges", icon: Layers },
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/session", label: "Session", icon: KeyRound },
  { to: "/settings", label: "Settings", icon: Cog },
];
