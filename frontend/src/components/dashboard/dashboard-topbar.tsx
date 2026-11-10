"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, LogOut, Menu, Settings, UserRound } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/components/auth/auth-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { initials, todayLong } from "@/lib/format";

const PAGE_TITLES: Array<{ prefix: string; title: string }> = [
  { prefix: "/dashboard/history", title: "Analysis history" },
  { prefix: "/dashboard/analysis", title: "Analysis results" },
  { prefix: "/dashboard/settings", title: "Account settings" },
  { prefix: "/dashboard", title: "Overview" },
];

export function DashboardTopbar({
  onOpenSidebar,
}: {
  onOpenSidebar: () => void;
}) {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const [signingOut, setSigningOut] = React.useState(false);

  const title =
    PAGE_TITLES.find((entry) => pathname.startsWith(entry.prefix))?.title ??
    "Overview";

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
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70 sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onOpenSidebar}
        aria-label="Open navigation"
      >
        <Menu className="size-5" />
      </Button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
          {title}
        </h1>
        <p className="hidden text-xs text-muted-foreground sm:block">
          {todayLong()}
        </p>
      </div>

      <div className="flex items-center gap-1">
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="gap-2 px-2 sm:px-2.5"
              aria-label="Account menu"
            >
              <Avatar className="size-7">
                <AvatarFallback className="text-[11px]">
                  {user ? initials(user.full_name) : "PH"}
                </AvatarFallback>
              </Avatar>
              <span className="hidden max-w-36 truncate text-sm font-medium sm:inline">
                {user?.full_name ?? "Account"}
              </span>
              <ChevronDown className="hidden size-4 text-muted-foreground sm:block" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="normal-case">
              <span className="block text-sm font-semibold text-foreground">
                {user?.full_name ?? "Planet Health"}
              </span>
              <span className="mt-0.5 block truncate text-xs font-normal text-muted-foreground">
                {user?.email ?? ""}
              </span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings">
                <UserRound />
                Account settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings#appearance">
                <Settings />
                Appearance
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => {
                void handleSignOut();
              }}
              disabled={signingOut}
            >
              <LogOut />
              {signingOut ? "Signing out…" : "Log out"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
