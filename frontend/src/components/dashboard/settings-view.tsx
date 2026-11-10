"use client";

import * as React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  LogOut,
  Monitor,
  Moon,
  Palette,
  Save,
  Sun,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth/auth-provider";
import { PasswordInput } from "@/components/auth/password-input";
import { useTheme } from "@/components/theme-provider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ApiError, authApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const THEME_OPTIONS = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
] as const;

export function SettingsView() {
  const { user, setUser, signOut } = useAuth();
  const { theme, setTheme } = useTheme();

  const [fullNameDraft, setFullNameDraft] = React.useState<string | null>(null);
  const fullName = fullNameDraft ?? user?.full_name ?? "";
  const [savingProfile, setSavingProfile] = React.useState(false);
  const [profileError, setProfileError] = React.useState<string | null>(null);
  const [profileSaved, setProfileSaved] = React.useState(false);

  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [changingPassword, setChangingPassword] = React.useState(false);
  const [passwordError, setPasswordError] = React.useState<string | null>(null);
  const [passwordSaved, setPasswordSaved] = React.useState(false);

  const [signingOut, setSigningOut] = React.useState(false);

  async function handleProfileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savingProfile) return;

    setProfileError(null);
    setProfileSaved(false);
    setSavingProfile(true);

    try {
      const updated = await authApi.updateProfile({ full_name: fullName.trim() });
      setUser(updated);
      setProfileSaved(true);
      toast.success("Your profile has been updated.");
    } catch (caught) {
      setProfileError(
        caught instanceof ApiError
          ? caught.message
          : "Your profile could not be updated.",
      );
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (changingPassword) return;

    setPasswordError(null);
    setPasswordSaved(false);

    if (newPassword !== confirmPassword) {
      setPasswordError("The new passwords do not match.");
      return;
    }

    setChangingPassword(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      });
      setPasswordSaved(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Your password has been updated. Please sign in again.");
      await signOut();
    } catch (caught) {
      setPasswordError(
        caught instanceof ApiError
          ? caught.message
          : "Your password could not be changed.",
      );
    } finally {
      setChangingPassword(false);
    }
  }

  async function handleSignOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
          Account settings
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your profile, password and appearance.
        </p>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Profile                                                       */}
      {/* ------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserRound className="size-[18px] text-primary" />
            Profile
          </CardTitle>
          <CardDescription>
            Your display name and the email address you sign in with.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            {profileError ? (
              <Alert variant="danger">
                <AlertCircle />
                <AlertDescription>{profileError}</AlertDescription>
              </Alert>
            ) : null}
            {profileSaved ? (
              <Alert variant="success">
                <CheckCircle2 />
                <AlertDescription>Your profile has been saved.</AlertDescription>
              </Alert>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="settings_full_name">Full name</Label>
                <Input
                  id="settings_full_name"
                  name="full_name"
                  autoComplete="name"
                  required
                  minLength={2}
                  value={fullName}
                  onChange={(event) => setFullNameDraft(event.target.value)}
                  disabled={savingProfile}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="settings_email">Email address</Label>
                <Input
                  id="settings_email"
                  name="email"
                  type="email"
                  value={user?.email ?? ""}
                  readOnly
                  disabled
                  className="bg-muted/50 text-muted-foreground"
                />
                <p className="text-xs text-muted-foreground">
                  The email address is used to sign in and cannot be changed
                  here.
                </p>
              </div>
            </div>

            <Button type="submit" disabled={savingProfile}>
              {savingProfile ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Save className="size-4" />
                  Save changes
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------- */}
      {/* Password                                                      */}
      {/* ------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>
            Changing your password signs you out of every session.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {passwordError ? (
              <Alert variant="danger">
                <AlertCircle />
                <AlertTitle>Could not change your password</AlertTitle>
                <AlertDescription>{passwordError}</AlertDescription>
              </Alert>
            ) : null}
            {passwordSaved ? (
              <Alert variant="success">
                <CheckCircle2 />
                <AlertDescription>
                  Your password has been updated.
                </AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="current_password">Current password</Label>
              <PasswordInput
                id="current_password"
                name="current_password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                disabled={changingPassword}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="new_password">New password</Label>
                <PasswordInput
                  id="new_password"
                  name="new_password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  disabled={changingPassword}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_new_password">Confirm new password</Label>
                <PasswordInput
                  id="confirm_new_password"
                  name="confirm_new_password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  disabled={changingPassword}
                />
              </div>
            </div>

            <Button type="submit" disabled={changingPassword}>
              {changingPassword ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Updating…
                </>
              ) : (
                "Update password"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------- */}
      {/* Appearance                                                    */}
      {/* ------------------------------------------------------------- */}
      <Card id="appearance" className="scroll-mt-24">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="size-[18px] text-primary" />
            Appearance
          </CardTitle>
          <CardDescription>
            Choose how Planet Health looks. The system option follows your
            operating system setting.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="inline-flex w-full max-w-md rounded-xl border border-border bg-muted/30 p-1">
            {THEME_OPTIONS.map(({ value, label, Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setTheme(value)}
                aria-pressed={theme === value}
                className={cn(
                  "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  theme === value
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ------------------------------------------------------------- */}
      {/* Session                                                      */}
      {/* ------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
          <CardDescription>
            Sign out of Planet Health on this device.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Separator className="mb-5" />
          <Button
            variant="outline"
            onClick={handleSignOut}
            disabled={signingOut}
            className="text-muted-foreground hover:text-destructive"
          >
            {signingOut ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Signing out…
              </>
            ) : (
              <>
                <LogOut className="size-4" />
                Log out
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
