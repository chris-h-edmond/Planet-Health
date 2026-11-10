import type { Metadata } from "next";

import { DashboardOverview } from "@/components/dashboard/dashboard-overview";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Upload a plant image and review your AI analysis history.",
};

export default function DashboardPage() {
  return <DashboardOverview />;
}
