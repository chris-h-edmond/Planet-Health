"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, Loader2, Lock } from "lucide-react";

import { PasswordInput } from "@/components/auth/password-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ApiError, authApi } from "@/lib/api";

export function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const passwordsMatch =
    confirmPassword.length === 0 || newPassword === confirmPassword;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setError(null);

    if (!token) {
      setError(
        "This password reset link is incomplete. Please request a new one.",
      );
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.resetPassword({
        token,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      });
      setDone(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Your password could not be changed. Please request a new link.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="space-y-6">
        <div className="space-y-1.5 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Password updated
          </h1>
          <p className="text-sm text-muted-foreground">
            Your password has been changed and every existing session was
            signed out.
          </p>
        </div>

        <Alert variant="success">
          <CheckCircle2 />
          <AlertDescription>
            You can now sign in with your new password.
          </AlertDescription>
        </Alert>

        <Button asChild className="w-full">
          <Link href="/login">Back to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Choose a new password
        </h1>
        <p className="text-sm text-muted-foreground">
          Your reset link is valid for 60 minutes and can only be used once.
        </p>
      </div>

      {error ? (
        <Alert variant="danger">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="space-y-2">
          <Label htmlFor="new_password">New password</Label>
          <PasswordInput
            id="new_password"
            name="new_password"
            autoComplete="new-password"
            placeholder="Create a new password"
            required
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            disabled={submitting}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm_new_password">Confirm new password</Label>
          <PasswordInput
            id="confirm_new_password"
            name="confirm_new_password"
            autoComplete="new-password"
            placeholder="Repeat your new password"
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            disabled={submitting}
            aria-invalid={!passwordsMatch}
          />
          {!passwordsMatch ? (
            <p className="text-xs text-destructive">
              The passwords do not match.
            </p>
          ) : null}
        </div>

        <Button type="submit" className="w-full" disabled={submitting || !token}>
          {submitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Updating…
            </>
          ) : (
            <>
              <Lock className="size-4" />
              Update password
            </>
          )}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
