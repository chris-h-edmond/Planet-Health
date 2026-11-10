"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Leaf, Sprout } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnalysisSummary } from "@/lib/types";
import { formatDateTime, formatPercent } from "@/lib/format";

function labelVariant(label: string): "success" | "danger" | "muted" {
  const normalised = label.toLowerCase();
  if (normalised.startsWith("healthy")) return "success";
  if (normalised.startsWith("stress")) return "danger";
  return "muted";
}

export function AnalysesTable({
  items,
  loading = false,
  showViewAction = true,
}: {
  items: AnalysisSummary[];
  loading?: boolean;
  showViewAction?: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden overflow-hidden rounded-xl border border-border lg:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-left">
              <th className="px-4 py-3 font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Analysis ID</span>
              </th>
              <th className="px-4 py-3 font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Date</span>
              </th>
              <th className="px-4 py-3 font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Classification</span>
              </th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Stress probability</span>
              </th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Leaf count</span>
              </th>
              <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                <span className="whitespace-nowrap">Est. age</span>
              </th>
              {showViewAction ? (
                <th className="px-4 py-3" />
              ) : null}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-border/70 transition-colors last:border-0 hover:bg-muted/30"
              >
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {item.id.slice(0, 8)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-foreground">
                  {formatDateTime(item.created_at)}
                </td>
                <td className="px-4 py-3">
                  <Badge variant={labelVariant(item.stress_label)}>
                    {item.stress_label}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-foreground">
                  {formatPercent(item.stress_score, 1)}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-foreground">
                  {item.leaf_count_rounded}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums whitespace-nowrap text-foreground">
                  {item.age_days.toFixed(1)} d
                </td>
                {showViewAction ? (
                  <td className="px-4 py-3 text-right">
                    <Button asChild variant="ghost" size="sm">
                      <Link
                        href={`/dashboard/analysis/${item.id}`}
                        aria-label={`View analysis ${item.id}`}
                      >
                        View
                        <ArrowUpRight className="size-4" />
                      </Link>
                    </Button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile / tablet cards */}
      <ul className="space-y-3 lg:hidden">
        {items.map((item) => (
          <li
            key={item.id}
            className="rounded-xl border border-border bg-card p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <Badge variant={labelVariant(item.stress_label)}>
                {item.stress_label}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground">
                {item.id.slice(0, 8)}
              </span>
            </div>

            <dl className="mt-3 grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  Stress prob.
                </dt>
                <dd className="mt-0.5 font-mono tabular-nums text-foreground">
                  {formatPercent(item.stress_score, 1)}
                </dd>
              </div>
              <div>
                <dt className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <Leaf className="size-3" />
                  Leaves
                </dt>
                <dd className="mt-0.5 font-mono tabular-nums text-foreground">
                  {item.leaf_count_rounded}
                </dd>
              </div>
              <div>
                <dt className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <Sprout className="size-3" />
                  Age
                </dt>
                <dd className="mt-0.5 font-mono tabular-nums text-foreground">
                  {item.age_days.toFixed(1)} d
                </dd>
              </div>
            </dl>

            <p className="mt-3 text-xs text-muted-foreground">
              {formatDateTime(item.created_at)}
            </p>

            {showViewAction ? (
              <Button asChild variant="outline" size="sm" className="mt-3 w-full">
                <Link href={`/dashboard/analysis/${item.id}`}>
                  View details
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </>
  );
}
