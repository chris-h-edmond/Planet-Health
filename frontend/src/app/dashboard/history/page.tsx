import type { Metadata } from "next";

import { HistoryView } from "@/components/dashboard/history-view";

export const metadata: Metadata = {
  title: "Analysis history",
  description: "Review every plant analysis you have run.",
};

export default function HistoryPage() {
  return <HistoryView />;
}
