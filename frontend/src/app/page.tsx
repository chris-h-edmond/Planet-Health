import Link from "next/link";
import {
  ArrowRight,
  Camera,
  ChartNoAxesColumn,
  FlaskConical,
  History,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Sprout,
} from "lucide-react";

import { HeroVisual } from "@/components/brand/hero-visual";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Plant stress detection",
    description:
      "A convolutional classifier separates healthy foliage from stressed foliage and reports the model's probability for each class.",
  },
  {
    icon: Sprout,
    title: "Growth estimation",
    description:
      "A regression model estimates leaf count and plant age in days directly from the image, giving you a baseline to track against.",
  },
  {
    icon: Camera,
    title: "Image-based analysis",
    description:
      "Upload a JPEG or PNG photograph and let the vision pipeline handle decoding, orientation, colour conversion and resizing.",
  },
  {
    icon: History,
    title: "Centralised history",
    description:
      "Every analysis is stored with its predictions and timestamp so you can review trends across a whole growing season.",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Upload a leaf image",
    description:
      "Take a photograph of a single leaf or plant and upload it as a JPEG or PNG file. Images are processed in memory and are not retained.",
  },
  {
    number: "02",
    title: "The AI processes the image",
    description:
      "Both research models run on the same image: one classifies plant stress, the other estimates leaf count and plant age.",
  },
  {
    number: "03",
    title: "Review the analysis",
    description:
      "Read the classification, the model stress probability and the growth estimates, then keep the record in your analysis history.",
  },
];

const MODEL_CARDS = [
  {
    icon: ShieldCheck,
    name: "Stress classification",
    type: "Binary classifier",
    outputs: ["Healthy / Stressed label", "Class probabilities"],
  },
  {
    icon: Sprout,
    name: "Growth estimation",
    type: "Multi-output regressor",
    outputs: ["Estimated leaf count", "Estimated plant age (days)"],
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />

      <main id="home" className="flex-1">
        {/* ---------------------------------------------------------------- */}
        {/* Hero                                                              */}
        {/* ---------------------------------------------------------------- */}
        <section className="relative overflow-hidden border-b border-border">
          <div
            aria-hidden="true"
            className="ph-grid-backdrop pointer-events-none absolute inset-0 opacity-60"
          />
          <div className="relative mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-16">
            <div className="max-w-xl">
              <Badge
                variant="secondary"
                className="mb-6 gap-1.5 border border-primary/20 bg-primary/10 text-primary"
              >
                <FlaskConical className="size-3.5" />
                Experimental research models
              </Badge>

              <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl lg:text-[3.25rem] lg:leading-[1.08]">
                Understand your plants through{" "}
                <span className="text-primary">AI-powered vision</span>
              </h1>

              <p className="mt-5 text-base leading-relaxed text-muted-foreground sm:text-lg">
                Planet Health classifies plant stress and estimates leaf count
                and plant age from a single photograph — so you can spot a
                struggling plant before it becomes a lost crop.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button asChild size="lg" className="w-full sm:w-auto">
                  <Link href="/register">
                    Start analysis
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="w-full sm:w-auto">
                  <Link href="#how-it-works">Learn more</Link>
                </Button>
              </div>

              <dl className="mt-10 grid max-w-lg grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-3">
                {[
                  { label: "Models in production pipeline", value: "2" },
                  { label: "Analysis latency", value: "CPU, on demand" },
                  { label: "Image retention", value: "None by default" },
                ].map((item) => (
                  <div key={item.label}>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {item.label}
                    </dt>
                    <dd className="mt-1 text-sm font-semibold text-foreground">
                      {item.value}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>

            <HeroVisual />
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Features                                                          */}
        {/* ---------------------------------------------------------------- */}
        <section id="features" className="scroll-mt-20 border-b border-border">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="max-w-2xl">
              <span className="text-sm font-semibold uppercase tracking-wide text-primary">
                Capabilities
              </span>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Everything you need to read a plant&apos;s condition
              </h2>
              <p className="mt-3 text-base leading-relaxed text-muted-foreground">
                One photograph, two models, and a history you can look back on.
              </p>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map((feature) => (
                <Card
                  key={feature.title}
                  interactive
                  className="h-full p-6"
                >
                  <span className="inline-flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <feature.icon className="size-5" />
                  </span>
                  <h3 className="mt-4 text-[15px] font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* How it works                                                      */}
        {/* ---------------------------------------------------------------- */}
        <section id="how-it-works" className="scroll-mt-20 border-b border-border bg-card/30">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="max-w-2xl">
              <span className="text-sm font-semibold uppercase tracking-wide text-primary">
                Workflow
              </span>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Three steps from photo to insight
              </h2>
            </div>

            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {STEPS.map((step) => (
                <li key={step.number}>
                  <Card className="h-full p-6">
                    <span className="font-mono text-sm font-semibold text-primary">
                      {step.number}
                    </span>
                    <h3 className="mt-3 text-[15px] font-semibold text-foreground">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {step.description}
                    </p>
                  </Card>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* About the technology                                              */}
        {/* ---------------------------------------------------------------- */}
        <section id="about" className="scroll-mt-20 border-b border-border">
          <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
            <div className="max-w-xl">
              <span className="text-sm font-semibold uppercase tracking-wide text-primary">
                About the technology
              </span>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Computer vision, purpose-built for greenhouse monitoring
              </h2>
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                Planet Health is built on PyTorch. Two trained checkpoints
                analyse every uploaded photograph: a stress classification
                model and a growth estimation model. Both run on the same
                pre-processed 224&times;224 image, so a single upload returns
                a combined result.
              </p>
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                The models are the product of active research. They have been
                smoke-tested for correct execution, but they are not yet
                scientifically validated for field deployment. Treat every
                output as an estimate and confirm anything important by
                inspecting the plant directly.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild variant="outline">
                  <Link href="/register">Create an account</Link>
                </Button>
                <Button asChild variant="ghost">
                  <Link href="/login">I already have one</Link>
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              {MODEL_CARDS.map((model) => (
                <Card key={model.name} className="p-6">
                  <div className="flex items-start gap-4">
                    <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <model.icon className="size-5" />
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-[15px] font-semibold text-foreground">
                        {model.name}
                      </h3>
                      <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
                        {model.type}
                      </p>
                      <ul className="mt-3 space-y-1.5">
                        {model.outputs.map((output) => (
                          <li
                            key={output}
                            className="flex items-center gap-2 text-sm text-muted-foreground"
                          >
                            <ScanLine className="size-3.5 shrink-0 text-primary" />
                            {output}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </Card>
              ))}

              <Card className="border-dashed bg-background/60 p-6">
                <div className="flex items-start gap-3">
                  <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Uploaded images are validated, processed in memory and
                    discarded. Only the prediction values and timestamps are
                    stored.
                  </p>
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Closing call to action                                            */}
        {/* ---------------------------------------------------------------- */}
        <section className="border-b border-border bg-primary/[0.04]">
          <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                Ready to run your first analysis?
              </h2>
              <p className="mt-2 text-base leading-relaxed text-muted-foreground">
                Create an account, upload a leaf photograph and read the
                results in seconds.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/register">
                  Get started
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/login">
                  Sign in
                  <ChartNoAxesColumn className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
