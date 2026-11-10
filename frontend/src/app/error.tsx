"use client";

import * as React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    // The digest can be correlated with the server logs.
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <span className="inline-flex size-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
        <AlertCircle className="size-7" />
      </span>
      <h2 className="mt-6 text-xl font-semibold tracking-tight text-foreground">
        Something went wrong
      </h2>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
        The page could not be rendered. Try again, and if the problem persists
        return to the dashboard.
      </p>
      <Button onClick={reset} className="mt-6">
        <RefreshCw className="size-4" />
        Try again
      </Button>
    </div>
  );
}
