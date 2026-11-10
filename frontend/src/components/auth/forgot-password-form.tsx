"use client";

import * as React from "react";
import Link from "next/link";
import { AlertCircle, Info, Loader2, MailCheck } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, authApi } from "@/lib/api";

export function ForgotPasswordForm() {
  const [email, setEmail] = React.useState("");
  const [error, setError] = React.useState<{
    code: string;
    message: string;
  } | null>(null);
  const [sent, setSent] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setError(null);
    setSubmitting(true);

    try {
      await authApi.forgotPassword(email.trim().toLowerCase());
      setSent(true);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError({ code: caught.code, message: caught.message });
      } else {
        setError({
          code: "REQUEST_FAILED",
          message: "Something went wrong. Please try again.",
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Reset your password
        </h1>
        <p className="text-sm text-muted-foreground">
          Enter the email address linked to your account and we&apos;ll send
          reset instructions.
        </p>
      </div>

      {error ? (
        <Alert variant={error.code === "EMAIL_DELIVERY_NOT_CONFIGURED" ? "warning" : "danger"}>
          {error.code === "EMAIL_DELIVERY_NOT_CONFIGURED" ? (
            <Info />
          ) : (
            <AlertCircle />
          )}
          <AlertTitle>
            {error.code === "EMAIL_DELIVERY_NOT_CONFIGURED"
              ? "Password reset is not available"
              : "Request failed"}
          </AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      ) : null}

      {sent ? (
        <Alert variant="success">
          <MailCheck />
          <AlertTitle>Check your inbox</AlertTitle>
          <AlertDescription>
            If an account exists for that address, a password reset email has
            been sent. The link is valid for 60 minutes and can only be used
            once.
          </AlertDescription>
        </Alert>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={submitting}
            />
          </div>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Sending…
              </>
            ) : (
              "Send reset instructions"
            )}
          </Button>
        </form>
      )}

      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
