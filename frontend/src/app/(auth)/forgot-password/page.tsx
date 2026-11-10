import type { Metadata } from "next";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export const metadata: Metadata = {
  title: "Reset your password",
  description: "Request a password reset for your Planet Health account.",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
