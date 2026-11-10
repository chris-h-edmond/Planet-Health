import type { Metadata } from "next";

import { SettingsView } from "@/components/dashboard/settings-view";

export const metadata: Metadata = {
  title: "Account settings",
  description: "Manage your Planet Health profile, password and appearance.",
};

export default function SettingsPage() {
  return <SettingsView />;
}
