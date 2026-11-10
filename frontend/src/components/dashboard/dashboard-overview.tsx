"use client";

import * as React from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  HeartPulse,
  History,
  Leaf,
  TriangleAlert,
} from "lucide-react";

import { AnalysesTable } from "@/components/dashboard/analyses-table";
import { StatCard } from "@/components/dashboard/stat-card";
import { UploadCard } from "@/components/dashboard/upload-card";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useModelStatus } from "@/hooks/use-model-status";
import { analysisApi, dashboardApi } from "@/lib/api";
import type { AnalysisSummary, DashboardStats } from "@/lib/types";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardOverview() {
  const { user } = useAuth();
  const { status: modelStatus, loading: modelLoading, reload } =
    useModelStatus();

  const [stats, setStats] = React.useState<DashboardStats | null>(null);
  const [statsLoading, setStatsLoading] = React.useState(true);
  const [statsError, setStatsError] = React.useState<string | null>(null);

  const [recent, setRecent] = React.useState<AnalysisSummary[]>([]);
  const [recentLoading, setRecentLoading] = React.useState(true);

  const loadStats = React.useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      setStats(await dashboardApi.stats());
    } catch {
      setStatsError("The dashboard statistics could not be loaded.");
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadRecent = React.useCallback(async () => {
    setRecentLoading(true);
    try {
      const result = await analysisApi.list({ page: 1, pageSize: 5 });
      setRecent(result.items);
    } catch {
      setRecent([]);
    } finally {
      setRecentLoading(false);
    }
  }, []);

  React.useEffect(() => {
    let active = true;

    (async () => {
      try {
        const next = await dashboardApi.stats();
        if (!active) return;
        setStats(next);
        setStatsError(null);
      } catch {
        if (!active) return;
        setStatsError("The dashboard statistics could not be loaded.");
      } finally {
        if (active) setStatsLoading(false);
      }

      try {
        const result = await analysisApi.list({ page: 1, pageSize: 5 });
        if (!active) return;
        setRecent(result.items);
      } catch {
        if (active) setRecent([]);
      } finally {
        if (active) setRecentLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------- */}
      {/* Welcome section                                              */}
      {/* ------------------------------------------------------------- */}
      <section className="rounded-xl border border-border bg-gradient-to-br from-secondary/60 via-card to-card p-6 sm:p-7">
        <p className="text-sm font-medium text-primary">
          {greeting()}, {firstName}
        </p>
        <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          Ready to check on your plants?
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Upload a leaf photograph and both research models will run against
          it — a stress classification and a growth estimate. Every result is
          saved to your history.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button asChild size="sm">
            <a href="#new-analysis">
              <Leaf className="size-4" />
              Analyse an image
            </a>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link href="/dashboard/history">
              <History className="size-4" />
              View history
            </Link>
          </Button>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* Summary cards                                                */}
      {/* ------------------------------------------------------------- */}
      <section aria-label="Summary statistics">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={Activity}
            label="Total analyses"
            value={stats?.total_analyses ?? 0}
            hint="All time"
            loading={statsLoading}
          />
          <StatCard
            icon={HeartPulse}
            label="Healthy"
            value={stats?.healthy_count ?? 0}
            hint={
              stats && stats.total_analyses > 0
                ? `${Math.round(stats.healthy_rate * 100)}% of analyses`
                : "No analyses yet"
            }
            tone="success"
            loading={statsLoading}
          />
          <StatCard
            icon={TriangleAlert}
            label="Stressed"
            value={stats?.stressed_count ?? 0}
            hint="Classified as stressed"
            tone="danger"
            loading={statsLoading}
          />
          <StatCard
            icon={History}
            label="Recent analyses"
            value={stats?.recent_analyses_count ?? 0}
            hint={`Last ${stats?.recent_window_days ?? 7} days`}
            tone="accent"
            loading={statsLoading}
          />
        </div>

        {statsError ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-muted/30 px-4 py-3">
            <p className="text-sm text-muted-foreground">{statsError}</p>
            <Button variant="outline" size="sm" onClick={() => void loadStats()}>
              Retry
            </Button>
          </div>
        ) : null}
      </section>

      {/* ------------------------------------------------------------- */}
      {/* New analysis                                                 */}
      {/* ------------------------------------------------------------- */}
      <UploadCard
        modelStatus={modelStatus}
        modelLoading={modelLoading}
        onAnalyzed={() => {
          void loadStats();
          void loadRecent();
        }}
      />

      {/* ------------------------------------------------------------- */}
      {/* Recent analyses                                              */}
      {/* ------------------------------------------------------------- */}
      <Card>
        <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
          <div>
            <CardTitle>Recent analyses</CardTitle>
            <CardDescription className="mt-1">
              Your five most recent plant analyses.
            </CardDescription>
          </div>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <Link href="/dashboard/history">
              View all
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {recentLoading ? (
            <AnalysesTable items={[]} loading />
          ) : recent.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center">
              <span className="inline-flex size-11 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <History className="size-5" />
              </span>
              <p className="mt-4 text-sm font-medium text-foreground">
                No analyses yet
              </p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                Upload your first plant image above — the result will appear
                here and in your full history.
              </p>
              <Button asChild size="sm" className="mt-4">
                <a href="#new-analysis">Analyse an image</a>
              </Button>
            </div>
          ) : (
            <AnalysesTable items={recent} />
          )}
        </CardContent>
      </Card>

      {/* Model status is surfaced here as well so that it is visible even
          when the user scrolls past the upload card. */}
      {modelStatus && !modelStatus.available ? (
        <p className="text-center text-xs text-muted-foreground">
          Model status:{" "}
          <span className="font-mono">{modelStatus.code}</span> —{" "}
          <button
            type="button"
            className="underline underline-offset-2 hover:text-foreground"
            onClick={() => void reload()}
          >
            re-check
          </button>
        </p>
      ) : null}
    </div>
  );
}
