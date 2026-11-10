"use client";

import { AlertTriangle, Leaf, ShieldCheck, Sprout } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { GrowthPrediction, StressPrediction } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

function isStressed(label: string): boolean {
  return label.toLowerCase().startsWith("stress");
}

export function StressPanel({
  stress,
  className,
}: {
  stress: StressPrediction;
  className?: string;
}) {
  const stressed = isStressed(stress.label);
  const healthyProbability = stress.probabilities.healthy;
  const stressedProbability = stress.probabilities.stressed;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-[18px] text-primary" />
              Plant stress classification
            </CardTitle>
            <CardDescription className="mt-1">
              Binary classifier trained on labelled leaf images.
            </CardDescription>
          </div>
          <Badge
            variant={stressed ? "danger" : "success"}
            className="px-3 py-1 text-sm"
          >
            {stress.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="rounded-xl border border-border bg-muted/30 p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Model stress probability
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={cn(
                "font-mono text-4xl font-semibold tabular-nums",
                stressed ? "text-destructive" : "text-success",
              )}
            >
              {formatNumber(stress.stress_score, 3)}
            </span>
            <span className="text-sm text-muted-foreground">
              on a {stress.score_scale} scale
            </span>
          </div>
          <Progress
            value={stressedProbability * 100}
            className="mt-4 h-1.5"
            indicatorClassName={stressed ? "bg-destructive" : "bg-success"}
          />
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            This is the model&apos;s confidence for the stressed class. It is not
            a validated measurement of biological stress severity.
          </p>
        </div>

        <dl className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-border p-4">
            <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Healthy probability
            </dt>
            <dd className="mt-1.5 font-mono text-2xl font-semibold tabular-nums text-foreground">
              {formatPercent(healthyProbability, 1)}
            </dd>
            <Progress
              value={healthyProbability * 100}
              className="mt-3 h-1.5"
              indicatorClassName="bg-success"
            />
          </div>
          <div className="rounded-xl border border-border p-4">
            <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Stressed probability
            </dt>
            <dd className="mt-1.5 font-mono text-2xl font-semibold tabular-nums text-foreground">
              {formatPercent(stressedProbability, 1)}
            </dd>
            <Progress
              value={stressedProbability * 100}
              className="mt-3 h-1.5"
              indicatorClassName="bg-destructive"
            />
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

export function GrowthPanel({
  growth,
  className,
}: {
  growth: GrowthPrediction;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sprout className="size-[18px] text-primary" />
              Plant growth estimation
            </CardTitle>
            <CardDescription className="mt-1">
              Multi-output regression model — both values come from the same
              image.
            </CardDescription>
          </div>
          <Badge variant="secondary" className="gap-1.5">
            <AlertTriangle className="size-3" />
            Experimental estimate
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-muted/30 p-5">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Leaf className="size-3.5" />
              Estimated leaf count
            </div>
            <p className="mt-2 font-mono text-4xl font-semibold tabular-nums text-foreground">
              {growth.leaf_count_rounded}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Raw model output: {formatNumber(growth.leaf_count, 2)}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-muted/30 p-5">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Sprout className="size-3.5" />
              Estimated plant age
            </div>
            <p className="mt-2 font-mono text-4xl font-semibold tabular-nums text-foreground">
              {formatNumber(growth.age_days, 1)}
              <span className="ml-1.5 text-base font-medium text-muted-foreground">
                days
              </span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Experimental — the current model reports an age MAE of roughly
              15.6 days.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
