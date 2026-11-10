"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  History,
  LayoutDashboard,
  LogOut,
  ScanLine,
  Settings,
  Sprout,
  X,
} from "lucide-react";

import { PlanetHealthLogo } from "@/components/brand/planet-health-logo";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    label: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    label: "New analysis",
    href: "/dashboard#new-analysis",
    icon: ScanLine,
    exact: false,
  },
  {
    label: "Analysis history",
    href: "/dashboard/history",
    icon: History,
    exact: false,
  },
  {
    label: "Account settings",
    href: "/dashboard/settings",
    icon: Settings,
    exact: false,
  },
];

export function DashboardSidebar({
  onNavigate,
}: {
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const { signOut } = useAuth();
  const [signingOut, setSigningOut] = React.useState(false);

  async function handleSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="flex h-full flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-5">
        <Link href="/" aria-label="Planet Health home">
          <PlanetHealthLogo />
        </Link>
        {onNavigate ? (
          <Button
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            onClick={onNavigate}
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </Button>
        ) : null}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Dashboard">
        {NAV_ITEMS.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href.split("#")[0]) &&
              item.href.split("#")[0] !== "/dashboard";

          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              <item.icon className="size-[18px] shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="mb-3 rounded-lg bg-sidebar-accent/60 px-3 py-2.5">
          <p className="flex items-center gap-1.5 text-xs font-medium text-sidebar-accent-foreground">
            <Sprout className="size-3.5" />
            Experimental models
          </p>
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
            Estimates only — verify anything important in the greenhouse.
          </p>
        </div>

        <Button
          variant="ghost"
          className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground"
          onClick={handleSignOut}
          disabled={signingOut}
        >
          <LogOut className="size-[18px]" />
          {signingOut ? "Signing out…" : "Logout"}
        </Button>
      </div>
    </div>
  );
}
