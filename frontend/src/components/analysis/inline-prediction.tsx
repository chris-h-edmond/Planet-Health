"use client";

import { GrowthPanel, StressPanel } from "@/components/analysis/prediction-panels";
import type { Prediction } from "@/lib/types";

/**
 * A compact rendering of a prediction, used when the backend returns a
 * result without a stored analysis id.
 */
export function InlinePrediction({
  prediction,
}: {
  prediction: Prediction;
}) {
  return (
    <div className="space-y-4 rounded-xl border border-border bg-muted/20 p-4">
      <p className="text-sm font-medium text-foreground">Prediction</p>
      <StressPanel stress={prediction.stress} />
      <GrowthPanel growth={prediction.growth} />
    </div>
  );
}
