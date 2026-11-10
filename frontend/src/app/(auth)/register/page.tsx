import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create an account",
  description: "Create a Planet Health account to analyse plant images.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
