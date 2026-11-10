import type { LucideIcon } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = "default",
  loading = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "success" | "danger" | "accent";
  loading?: boolean;
}) {
  const toneClasses = {
    default: "bg-primary/10 text-primary",
    success: "bg-[color-mix(in_srgb,var(--success)_14%,transparent)] text-success",
    danger:
      "bg-[color-mix(in_srgb,var(--destructive)_14%,transparent)] text-destructive",
    accent: "bg-muted text-muted-foreground",
  }[tone];

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          {loading ? (
            <div className="mt-2 h-8 w-16 animate-pulse rounded-md bg-muted" />
          ) : (
            <p className="mt-1.5 font-mono text-3xl font-semibold tabular-nums text-foreground">
              {value}
            </p>
          )}
          {hint ? (
            <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
          ) : null}
        </div>
        <span
          className={cn(
            "inline-flex size-9 shrink-0 items-center justify-center rounded-lg",
            toneClasses,
          )}
        >
          <Icon className="size-[18px]" />
        </span>
      </div>
    </Card>
  );
}
