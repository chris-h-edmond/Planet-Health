"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ImageIcon,
  Info,
  Loader2,
  RefreshCw,
  ScanLine,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, analysisApi } from "@/lib/api";
import type { ModelStatus, Prediction } from "@/lib/types";
import { cn } from "@/lib/utils";
import { InlinePrediction } from "@/components/analysis/inline-prediction";

const MAX_UPLOAD_SIZE_MB = Number(
  process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB ?? 10,
);
const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

const ACCEPTED_MIME_TYPES = ["image/jpeg", "image/png"];
const ACCEPTED_EXTENSIONS = ["jpg", "jpeg", "png"];
const ACCEPT_ATTRIBUTE = "image/jpeg,image/png,.jpg,.jpeg,.png";

function extensionOf(name: string): string {
  const parts = name.toLowerCase().split(".");
  return parts.length > 1 ? parts[parts.length - 1] : "";
}

function validateFile(file: File): string | null {
  const extension = extensionOf(file.name);
  const typeLooksValid =
    ACCEPTED_MIME_TYPES.includes(file.type) ||
    ACCEPTED_EXTENSIONS.includes(extension);

  if (!typeLooksValid) {
    return "Only JPEG and PNG images are supported.";
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return `The image is larger than the ${MAX_UPLOAD_SIZE_MB} MB limit.`;
  }
  if (file.size === 0) {
    return "The selected file is empty.";
  }
  return null;
}

export function UploadCard({
  modelStatus,
  modelLoading,
  onAnalyzed,
}: {
  modelStatus: ModelStatus | null;
  modelLoading: boolean;
  onAnalyzed?: () => void;
}) {
  const router = useRouter();
  const inputRef = React.useRef<HTMLInputElement>(null);
  const previewUrlRef = React.useRef<string | null>(null);

  const [file, setFile] = React.useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [inlinePrediction, setInlinePrediction] =
    React.useState<Prediction | null>(null);

  const modelsAvailable = modelStatus?.available === true;
  const modelsKnown = !modelLoading && modelStatus !== null;

  React.useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, []);

  function applyFile(next: File | null) {
    // Validate before discarding the current selection so that a rejected
    // file never destroys a perfectly good one.
    if (next) {
      const validationError = validateFile(next);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setPreviewUrl(null);
    setFile(null);
    setError(null);
    setInlinePrediction(null);

    if (!next) return;

    const url = URL.createObjectURL(next);
    previewUrlRef.current = url;
    setPreviewUrl(url);
    setFile(next);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (submitting) return;
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) applyFile(dropped);
  }

  function handleBrowse(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    applyFile(selected);
    // Allow re-selecting the same file.
    event.target.value = "";
  }

  async function handleAnalyze() {
    if (!file || submitting) return;

    setError(null);
    setInlinePrediction(null);
    setSubmitting(true);

    try {
      const result = await analysisApi.predict(file);
      onAnalyzed?.();

      if (result.analysisId) {
        toast.success("Analysis complete.");
        router.push(`/dashboard/analysis/${result.analysisId}`);
        return;
      }

      // Fallback: the backend did not return an analysis id.
      setInlinePrediction(result.prediction);
      toast.success("Analysis complete.");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
        if (caught.code === "MODEL_NOT_CONFIGURED" || caught.code === "MODEL_LOAD_FAILED") {
          toast.error("The analysis models are not available.");
        }
      } else {
        setError("The analysis could not be completed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card id="new-analysis" className="scroll-mt-24">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>New plant analysis</CardTitle>
            <CardDescription className="mt-1">
              Upload a clear photograph of a leaf. Both models analyse the same
              image.
            </CardDescription>
          </div>
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
            JPEG · PNG · max {MAX_UPLOAD_SIZE_MB} MB
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {modelsKnown && !modelsAvailable ? (
          <Alert variant="warning">
            <Info />
            <AlertTitle>
              {modelStatus?.status === "failed"
                ? "The analysis models failed to start"
                : "Model integration is pending"}
            </AlertTitle>
            <AlertDescription>
              {modelStatus?.message ??
                "Plant analysis models are not configured."}{" "}
              {modelStatus?.detail ? `(${modelStatus.detail})` : ""} The
              interface below is fully functional — the prediction endpoint
              will answer with HTTP 503 until the model checkpoints are
              installed.
            </AlertDescription>
          </Alert>
        ) : null}

        {error ? (
          <Alert variant="danger">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {/* ---------------------------------------------------------- */}
        {/* Drop zone / preview                                        */}
        {/* ---------------------------------------------------------- */}
        {previewUrl && file ? (
          <div className="overflow-hidden rounded-xl border border-border bg-muted/30">
            <div className="relative aspect-[16/9] w-full bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Selected plant image preview"
                className="size-full object-contain"
              />
              {submitting ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm">
                  <Loader2 className="size-7 animate-spin text-primary" />
                  <p className="text-sm font-medium text-foreground">
                    Analyzing plant image…
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Running the stress and growth models
                  </p>
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {file.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB ·{" "}
                  {file.type || "image"}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => inputRef.current?.click()}
                  disabled={submitting}
                >
                  <RefreshCw className="size-4" />
                  Replace
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => applyFile(null)}
                  disabled={submitting}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                  Remove
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(event) => {
              event.preventDefault();
              if (!submitting) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            aria-label="Upload a plant image"
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
              dragging
                ? "border-primary bg-primary/[0.06]"
                : "border-border bg-muted/20 hover:border-primary/50 hover:bg-muted/40",
              submitting && "pointer-events-none opacity-60",
            )}
          >
            <span className="inline-flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Upload className="size-6" />
            </span>
            <p className="mt-4 text-sm font-medium text-foreground">
              Drag and drop a plant image here
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              or{" "}
              <span className="font-medium text-primary">browse your files</span>
            </p>
            <p className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
              <ImageIcon className="size-3.5" />
              JPEG or PNG · up to {MAX_UPLOAD_SIZE_MB} MB · not retained after
              processing
            </p>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTRIBUTE}
          className="sr-only"
          onChange={handleBrowse}
          disabled={submitting}
          aria-hidden="true"
          tabIndex={-1}
        />

        {/* ---------------------------------------------------------- */}
        {/* Actions                                                    */}
        {/* ---------------------------------------------------------- */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-relaxed text-muted-foreground">
            By analysing an image you confirm that you are happy for it to be
            processed for this request. Images are processed in memory and are
            not stored.
          </p>

          <Button
            onClick={handleAnalyze}
            disabled={!file || submitting}
            className="w-full sm:w-auto"
            size="lg"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Analyzing plant image…
              </>
            ) : (
              <>
                <ScanLine className="size-4" />
                Analyze plant
              </>
            )}
          </Button>
        </div>

        {inlinePrediction ? (
          <InlinePrediction prediction={inlinePrediction} />
        ) : null}
      </CardContent>
    </Card>
  );
}
