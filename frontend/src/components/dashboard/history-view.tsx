"use client";

import * as React from "react";
import Link from "next/link";
import { AlertCircle, ChevronLeft, ChevronRight, History, ScanLine } from "lucide-react";

import { AnalysesTable } from "@/components/dashboard/analyses-table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { analysisApi } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";

const PAGE_SIZE = 20;

export function HistoryView() {
  const [items, setItems] = React.useState<AnalysisSummary[]>([]);
  const [page, setPage] = React.useState(1);
  const [total, setTotal] = React.useState(0);
  const [totalPages, setTotalPages] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(
    async (targetPage: number) => {
      setLoading(true);
      setError(null);
      try {
        const result = await analysisApi.list({
          page: targetPage,
          pageSize: PAGE_SIZE,
        });
        setItems(result.items);
        setTotal(result.total);
        setTotalPages(result.total_pages);
        setPage(result.page);
      } catch {
        setError("The analysis history could not be loaded.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  React.useEffect(() => {
    let active = true;

    (async () => {
      try {
        const result = await analysisApi.list({ page: 1, pageSize: PAGE_SIZE });
        if (!active) return;
        setItems(result.items);
        setTotal(result.total);
        setTotalPages(result.total_pages);
        setPage(result.page);
      } catch {
        if (!active) return;
        setError("The analysis history could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
            Analysis history
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Every analysis you have run, newest first.
            {total > 0 ? ` ${total} recorded.` : ""}
          </p>
        </div>

        <Button asChild>
          <Link href="/dashboard#new-analysis">
            <ScanLine className="size-4" />
            New analysis
          </Link>
        </Button>
      </div>

      {error ? (
        <Alert variant="danger">
          <AlertCircle />
          <AlertTitle>Could not load your history</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardContent className="pt-5 sm:pt-6">
          {loading ? (
            <AnalysesTable items={[]} loading />
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border px-6 py-16 text-center">
              <span className="inline-flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <History className="size-6" />
              </span>
              <p className="mt-4 text-base font-medium text-foreground">
                No analyses yet
              </p>
              <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
                Once you analyse a plant image, the result and its timestamp
                will be listed here.
              </p>
              <Button asChild className="mt-6">
                <Link href="/dashboard#new-analysis">
                  <ScanLine className="size-4" />
                  Analyse your first image
                </Link>
              </Button>
            </div>
          ) : (
            <>
              <AnalysesTable items={items} />
              {totalPages > 1 ? (
                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
                  <p className="text-xs text-muted-foreground">
                    Page {page} of {totalPages} · {total} analyses
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1 || loading}
                      onClick={() => void load(page - 1)}
                    >
                      <ChevronLeft className="size-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages || loading}
                      onClick={() => void load(page + 1)}
                    >
                      Next
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
