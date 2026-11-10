import type { Metadata } from "next";

import { AnalysisDetailView } from "@/components/analysis/analysis-detail-view";

export const metadata: Metadata = {
  title: "Analysis results",
  description: "Review the stress classification and growth estimation results.",
};

export default async function AnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AnalysisDetailView analysisId={id} />;
}
