"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  History,
  Info,
  Loader2,
  ScanLine,
} from "lucide-react";

import { GrowthPanel, StressPanel } from "@/components/analysis/prediction-panels";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, analysisApi } from "@/lib/api";
import type { AnalysisDetail } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

export function AnalysisDetailView({ analysisId }: { analysisId: string }) {
  const [analysis, setAnalysis] = React.useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [notFound, setNotFound] = React.useState(false);

  React.useEffect(() => {
    let active = true;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await analysisApi.get(analysisId);
        if (!active) return;
        setAnalysis(result);
      } catch (caught) {
        if (!active) return;
        if (caught instanceof ApiError && caught.status === 404) {
          setNotFound(true);
        } else {
          setError(
            caught instanceof ApiError
              ? caught.message
              : "The analysis could not be loaded.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [analysisId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-56 w-full rounded-xl" />
        <Skeleton className="h-56 w-full rounded-xl" />
      </div>
    );
  }

  if (notFound) {
    return (
      <Card className="mx-auto max-w-lg">
        <CardContent className="flex flex-col items-center px-6 py-14 text-center">
          <span className="inline-flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <AlertCircle className="size-6" />
          </span>
          <h2 className="mt-4 text-lg font-semibold text-foreground">
            Analysis not found
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            This analysis does not exist, or it belongs to a different account.
          </p>
          <Button asChild className="mt-6">
            <Link href="/dashboard/history">Back to history</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (error || !analysis) {
    return (
      <Alert variant="danger">
        <AlertCircle />
        <AlertTitle>Could not load the analysis</AlertTitle>
        <AlertDescription>
          {error ?? "An unexpected error occurred."}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------- */}
      {/* Header                                                       */}
      {/* ------------------------------------------------------------- */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="-ml-2 mb-2 text-muted-foreground"
          >
            <Link href="/dashboard">
              <ArrowLeft className="size-4" />
              Back to dashboard
            </Link>
          </Button>
          <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            Analysis results
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Produced {formatDateTime(analysis.created_at)}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link href="/dashboard#new-analysis">
              <ScanLine className="size-4" />
              Analyze another image
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/dashboard/history">
              <History className="size-4" />
              View history
            </Link>
          </Button>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Disclaimer                                                   */}
      {/* ------------------------------------------------------------- */}
      <Alert variant="warning">
        <Info />
        <AlertTitle>Experimental estimates</AlertTitle>
        <AlertDescription>
          These results are AI-generated estimates from experimental
          computer-vision models. They should not replace direct plant
          inspection or validated agricultural assessment.
        </AlertDescription>
      </Alert>

      {/* ------------------------------------------------------------- */}
      {/* Model outputs                                                */}
      {/* ------------------------------------------------------------- */}
      <div className="grid gap-4 xl:grid-cols-2">
        <StressPanel stress={analysis.stress} />
        <GrowthPanel growth={analysis.growth} />
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Metadata                                                    */}
      {/* ------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Analysis metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Analysis ID
              </dt>
              <dd className="mt-1 break-all font-mono text-sm text-foreground">
                {analysis.id}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Date &amp; time
              </dt>
              <dd className="mt-1 text-sm text-foreground">
                {formatDateTime(analysis.created_at)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Stress score scale
              </dt>
              <dd className="mt-1 font-mono text-sm text-foreground">
                {analysis.stress.score_scale}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Prediction source
              </dt>
              <dd className="mt-1 text-sm text-foreground">
                Stress classifier &amp; growth regressor
              </dd>
            </div>
          </dl>

          <Separator className="my-5" />

          <div className="flex items-start gap-3 rounded-lg bg-muted/40 px-4 py-3">
            <Camera className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <p className="text-xs leading-relaxed text-muted-foreground">
              Uploaded images are not retained. This record stores only the
              prediction values and the timestamp of the analysis.
            </p>
          </div>
        </CardContent>
      </Card>

      {error ? (
        <p className="flex items-center gap-2 text-sm text-destructive">
          <Loader2 className="size-4" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
