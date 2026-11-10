/**
 * The hero visual.
 *
 * A stylized "scan" of a plant leaf rendered entirely in SVG so that the
 * landing page stays self-contained (no external image hosts, no licensing
 * questions, no layout shift).
 */
export function HeroVisual() {
  return (
    <div className="relative">
      <div
        aria-hidden="true"
        className="ph-grid-backdrop absolute -inset-6 rounded-[2rem] opacity-70"
      />

      <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-[0_24px_60px_-24px_rgba(16,32,22,0.35)]">
        {/* Window chrome */}
        <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-3">
          <span className="size-2.5 rounded-full bg-destructive/60" />
          <span className="size-2.5 rounded-full bg-warning/60" />
          <span className="size-2.5 rounded-full bg-success/60" />
          <span className="ml-3 font-mono text-[11px] text-muted-foreground">
            groMo25 · leaf-041.jpg
          </span>
        </div>

        <div className="relative aspect-[4/3] w-full bg-gradient-to-br from-secondary/60 via-background to-background">
          {/* Leaf illustration */}
          <svg
            viewBox="0 0 400 300"
            className="absolute inset-0 size-full"
            fill="none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="leaf" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#3E8F63" />
                <stop offset="55%" stopColor="#276749" />
                <stop offset="100%" stopColor="#174C38" />
              </linearGradient>
              <linearGradient id="leafAlt" x1="0" y1="1" x2="1" y2="0">
                <stop offset="0%" stopColor="#5AA97B" />
                <stop offset="100%" stopColor="#2F7D51" />
              </linearGradient>
            </defs>

            <path
              d="M196 268c-4-52 6-92 34-124 22-26 54-42 96-46-2 44-16 82-44 112-26 28-56 46-86 58Z"
              fill="url(#leaf)"
            />
            <path
              d="M198 268c-2-38-16-72-42-100-24-26-56-42-94-46 2 44 16 82 44 112 24 26 56 44 92 34Z"
              fill="url(#leafAlt)"
              opacity="0.95"
            />
            <path
              d="M200 270c0-46 14-84 44-114"
              stroke="#E8F3EC"
              strokeOpacity="0.35"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <path
              d="M198 268c-8-38-24-68-50-94"
              stroke="#E8F3EC"
              strokeOpacity="0.3"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <path
              d="M228 186c14-16 30-28 50-36M228 186c2-16 0-30-6-42M172 198c-16-12-32-20-50-24M172 198c-4-14-4-26-2-38"
              stroke="#E8F3EC"
              strokeOpacity="0.22"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>

          {/* Scan brackets */}
          <div className="absolute inset-6">
            <span className="absolute left-0 top-0 size-8 rounded-tl-lg border-l-2 border-t-2 border-primary/70" />
            <span className="absolute right-0 top-0 size-8 rounded-tr-lg border-r-2 border-t-2 border-primary/70" />
            <span className="absolute bottom-0 left-0 size-8 rounded-bl-lg border-b-2 border-l-2 border-primary/70" />
            <span className="absolute bottom-0 right-0 size-8 rounded-br-lg border-b-2 border-r-2 border-primary/70" />
          </div>

          {/* Scan line */}
          <div className="absolute inset-x-6 top-1/2 h-px bg-gradient-to-r from-transparent via-primary/70 to-transparent" />

          {/* Readout chips */}
          <div className="absolute bottom-4 left-4 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/90 px-2.5 py-1 text-[11px] font-medium text-foreground backdrop-blur">
              <span className="size-1.5 rounded-full bg-success" />
              Healthy
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/90 px-2.5 py-1 text-[11px] font-medium text-foreground backdrop-blur">
              <svg viewBox="0 0 24 24" className="size-3" fill="none" aria-hidden="true">
                <path
                  d="M12 21c0-6 3-10 8-11-.5 5-3.5 9-8 11Zm0 0c0-6-3-10-8-11 .5 5 3.5 9 8 11Z"
                  className="stroke-current"
                  strokeWidth="1.6"
                  strokeLinejoin="round"
                />
              </svg>
              8 leaves
            </span>
          </div>
        </div>

        {/* Footer readout */}
        <div className="grid grid-cols-3 divide-x divide-border border-t border-border bg-muted/30">
          {[
            { label: "Stress probability", value: "0.13" },
            { label: "Leaf count", value: "8" },
            { label: "Est. age", value: "26 d" },
          ].map((item) => (
            <div key={item.label} className="px-4 py-3">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                {item.label}
              </p>
              <p className="mt-1 font-mono text-sm font-semibold text-foreground">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
