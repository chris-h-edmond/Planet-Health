import { cn } from "@/lib/utils";

/** The Planet Health leaf mark. Inherits the current text colour. */
export function LeafMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      className={cn("size-8", className)}
      fill="none"
      aria-hidden="true"
    >
      <rect
        width="40"
        height="40"
        rx="11"
        className="fill-primary/12"
      />
      <path
        d="M28.8 11.2c.6 9.4-4.6 15.2-11.2 15.2-2 0-3.6-.4-4.9-1.1-.2-7.4 3.4-12.7 8.6-14.7 2.4-.9 4.9-1 7.5-.7v1.3Z"
        className="fill-primary"
      />
      <path
        d="M12.9 30.4c2.4-6.2 6.4-10.6 11.6-12.6"
        className="stroke-primary"
        strokeOpacity="0.45"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** The full Planet Health logo lock-up. */
export function PlanetHealthLogo({
  className,
  showWordmark = true,
}: {
  className?: string;
  showWordmark?: boolean;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LeafMark className="size-8 shrink-0" />
      {showWordmark ? (
        <span className="text-[17px] font-semibold tracking-tight text-foreground">
          Planet Health
        </span>
      ) : null}
    </span>
  );
}
